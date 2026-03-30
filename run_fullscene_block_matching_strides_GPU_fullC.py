import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from osgeo import gdal
from osgeo import osr
from skimage import measure

gdal.UseExceptions()
import os, logging, time, sys, tqdm
import cupy as cp
import numba as nb

mempool = cp.get_default_memory_pool()
pinned_mempool = cp.get_default_pinned_memory_pool()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def get_basis(x, y, max_order=4):
    """Return the fit basis polynomials: 1, x, x^2, ..., xy, x^2y, ... etc."""
    basis = []
    for i in range(max_order + 1):
        for j in range(max_order - i + 1):
            basis.append(x**j * y**i)
    return basis


def write_patch_correlation_npy(u, v, block_sizes, correlation, dirname, fname):
    fname_u = os.path.join(dirname, fname + "_u.npy")
    np.save(fname_u, u)
    fname_v = os.path.join(dirname, fname + "_v.npy")
    np.save(fname_v, v)
    fname_bs = os.path.join(dirname, fname + "_bs.npy")
    np.save(fname_bs, block_sizes)
    fname_c = os.path.join(dirname, fname + "_correlation.npy")
    np.save(fname_c, correlation)


def load_mask_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint8")
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, int(epsg)


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint16")
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, int(epsg)


def get_geotiff_info(geotiff_fn):
    """
    Get Geotiff information from fn.
    """
    ds = gdal.Open(geotiff_fn)
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    epsg = osr.SpatialReference(wkt=proj).GetAttrValue("AUTHORITY", 1)

    data = ds.ReadAsArray()
    ys, xs = data.shape
    ds = None
    return gt, proj, epsg, ys, xs


def save_mask_geotiff(geotiff_fn, array, epsg_code, geotransform):
    # mask value is 1 - all values with 1 are masked out (True)
    xdim = array.shape[0]
    ydim = array.shape[1]

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)

    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outRaster = driver.Create(
        geotiff_fn,
        ydim,
        xdim,
        1,
        gdal.GDT_Byte,
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
    )
    outRaster.SetGeoTransform(geotransform)
    outRaster.SetProjection(srs.ExportToProj4())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.FlushCache()
    outband.ComputeStatistics(0)
    outband.FlushCache()
    del outband, outRaster, driver


def save_c_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=0):
    xdim = array.shape[0]
    ydim = array.shape[1]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outRaster = driver.Create(
        geotiff_fn,
        ydim,
        xdim,
        1,
        gdal.GDT_Byte,  # GDT_Byte is an 8 bit unsigned integer
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
    )
    outRaster.SetGeoTransform(geotransform)
    outRaster.SetProjection(srs.ExportToProj4())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.FlushCache()
    outband.SetNoDataValue(nan_value)
    outband.ComputeStatistics(0)
    outband.FlushCache()
    del outband, outRaster, driver


def save_float32_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=np.nan):
    xdim = array.shape[0]
    ydim = array.shape[1]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outRaster = driver.Create(
        geotiff_fn,
        ydim,
        xdim,
        1,
        gdal.GDT_Float32,
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=3"],
    )
    outRaster.SetGeoTransform(geotransform)
    outRaster.SetProjection(srs.ExportToProj4())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.FlushCache()
    outband.SetNoDataValue(nan_value)
    outband.ComputeStatistics(0)
    outband.FlushCache()
    del outband, outRaster, driver


def save_uv_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=-128):
    xdim = array.shape[0]
    ydim = array.shape[1]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outRaster = driver.Create(
        geotiff_fn,
        ydim,
        xdim,
        1,
        gdal.GDT_Int8,
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
    )
    outRaster.SetGeoTransform(geotransform)
    outRaster.SetProjection(srs.ExportToProj4())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.FlushCache()
    outband.SetNoDataValue(nan_value)
    outband.ComputeStatistics(0)
    outband.FlushCache()
    del outband, outRaster, driver


def save_all_geotiff(tifdirname):
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_u.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(
        geotiff_fn,
        u,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_v.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(geotiff_fn, v, int(epsg_code), geotransform=Landsat_1_ds_gt)
    # geotiff_fn = os.path.join(
    #     tifdirname,
    #     os.path.basename(dirname)
    #     + "_bs%02d_sr%02d_ms%02d_blocksizes.tif"
    #     % (
    #         block_size,
    #         search_radius,
    #         matching_step,
    #     ),
    # )
    # logging.info("Save geotiff to %s" % (geotiff_fn))
    # save_geotiff(
    #     geotiff_fn,
    #     block_sizes,
    #     int(epsg_code),
    #     geotransform=Landsat_1_ds_gt,
    # )
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_correlation.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_c_geotiff(
        geotiff_fn,
        correlation,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )


def fit_polynD_cupy_ar(A4, B, B_fine, cc_gpu, coords_fine_gpu):
    Z, _, _, _ = cp.linalg.lstsq(A4, cc_gpu.T, rcond=None)
    Zi = cp.sum(Z[:, None, :] * B[:, :, None], axis=0)
    dz_pn = cc_gpu.T - Zi
    pn_rmse = cp.asnumpy(cp.sqrt(cp.mean(cp.square(dz_pn), axis=0)))
    dz_pn = None
    cc_gpu = None
    Zi = None
    del cc_gpu, Zi, dz_pn
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    # create fine mesh for evaluating function
    Zi_fine = cp.sum(Z[:, None, :] * B_fine[:, :, None], axis=0)
    Zi_argmax_gpu = cp.argmax(Zi_fine, axis=0)
    Zi_pn_fine_x = cp.asnumpy(coords_fine_gpu[Zi_argmax_gpu, 0])
    Zi_pn_fine_y = cp.asnumpy(coords_fine_gpu[Zi_argmax_gpu, 1])
    Zi_fine = None
    Z = None
    Zi_argmax_gpu = None
    del (
        Zi_fine,
        Z,
        Zi_argmax_gpu,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    return pn_rmse, Zi_pn_fine_x, Zi_pn_fine_y


def fit_polynD_GPU_ar(coords, corrcoef_ar, coords_fine, max_order=4, nr_ar_splits=1000):
    basis = get_basis(coords[:, 0], coords[:, 1], max_order)
    # fitting nth-order polynomial
    A = cp.asarray(np.vstack(basis).T, dtype=cp.float32)
    cc_gpu = cp.asarray(corrcoef_ar, dtype=cp.float32)
    Z, _, _, _ = cp.linalg.lstsq(A, cc_gpu.T, rcond=None)
    # B = cp.array(
    #     get_basis(coords[:, 0], coords[:, 1], max_order), dtype=cp.float32
    # ).reshape(len(basis), coords.shape[0])
    # The matrix multiplication on the gpu uses too much memory
    # Zi = cp.sum(Z[:, None, :] * B[:, :, None], axis=0)
    B = np.array(
        get_basis(coords[:, 0], coords[:, 1], max_order), dtype=np.float32
    ).reshape(len(basis), coords.shape[0])
    Zi = np.sum(cp.asnumpy(Z[:, None, :]) * cp.asnumpy(B[:, :, None]), axis=0)
    # This multiplies the two variables via a for loop. Very slow, but more memory efficient:
    # Zi = cp.empty( (Z.shape[1], coords.shape[0]), dtype=cp.float32)
    # Zi.fill(cp.nan)
    #
    # for i in range(Z.shape[1]):
    #     Zi[i,:] = cp.sum( Z[:, i, None] * B, axis=0)
    # Zi = Zi.T
    dz_pn = corrcoef_ar.T - Zi
    pn_rmse = np.sqrt(np.mean(np.square(dz_pn), axis=0))
    dz_pn = None
    A = None
    B = None
    cc_gpu = None
    Zi = None
    del A, cc_gpu, Zi
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()

    # create fine mesh for evaluating function
    coords_fine_gpu = cp.asarray(coords_fine, dtype=cp.float32)
    Zi_pn_fine_gpu_x = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_pn_fine_gpu_x.fill(cp.nan)
    Zi_pn_fine_gpu_y = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_pn_fine_gpu_y.fill(cp.nan)
    B = cp.array(
        get_basis(coords_fine[:, 0], coords_fine[:, 1], max_order), dtype=cp.float32
    ).reshape(len(basis), coords_fine.shape[0])
    for ii in range(nr_ar_splits):
        Z_cp_tile = cp.array_split(Z, nr_ar_splits, axis=1)[ii]
        Zi_fine = cp.sum(Z_cp_tile[:, None, :] * B[:, :, None], axis=0)
        Zi_argmax_gpu = cp.argmax(Zi_fine, axis=0)
        Zi_pn_fine_gpu_x[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[Zi_argmax_gpu, 0]
        Zi_pn_fine_gpu_y[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[Zi_argmax_gpu, 1]
    Zi_pn_fine_gpu_x = cp.concatenate(Zi_pn_fine_gpu_x)
    Zi_pn_fine_gpu_x = Zi_pn_fine_gpu_x[~cp.isnan(Zi_pn_fine_gpu_x)]
    Zi_pn_fine_x = cp.asnumpy(Zi_pn_fine_gpu_x)
    Zi_pn_fine_gpu_y = cp.concatenate(Zi_pn_fine_gpu_y)
    Zi_pn_fine_gpu_y = Zi_pn_fine_gpu_y[~cp.isnan(Zi_pn_fine_gpu_y)]
    Zi_pn_fine_y = cp.asnumpy(Zi_pn_fine_gpu_y)
    Zi_pn_fine_gpu_x = None
    Zi_pn_fine_gpu_y = None
    coords_fine_gpu = None
    Z_cp_tile = None
    Zi_fine = None
    Z = None
    B = None
    Zi_argmax_gpu = None
    del (
        Zi_pn_fine_gpu_x,
        Zi_pn_fine_gpu_y,
        coords_fine_gpu,
        Z_cp_tile,
        Zi_fine,
        Z,
        B,
        Zi_argmax_gpu,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    return pn_rmse, Zi_pn_fine_x, Zi_pn_fine_y


def fit_poly2D_cupy_ar(A, coords_gpu, cc_gpu, coords_fine_gpu):
    # fitting second order polynomial
    Z, _, _, _ = cp.linalg.lstsq(A, cc_gpu.T, rcond=None)
    Zi = (
        Z[0, :]
        + Z[1, :] * coords_gpu[:, 0, None]
        + Z[2, :] * coords_gpu[:, 1, None]
        + Z[3, :] * cp.prod(coords_gpu[:, cp.newaxis], axis=2)
        + Z[4, :] * coords_gpu[:, 0, None] ** 2
        + Z[5, :] * coords_gpu[:, 1, None] ** 2
    )
    dz_p2 = cc_gpu.T - Zi
    p2_rmse = cp.asnumpy(cp.sqrt(cp.mean(cp.square(dz_p2), axis=0)))
    dz_p2 = None
    cc_gpu = None
    Zi = None
    del cc_gpu, Zi
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    #
    Zi_fine = (
        Z[0, :]
        + Z[1, :] * coords_fine_gpu[:, 0, None]
        + Z[2, :] * coords_fine_gpu[:, 1, None]
        + Z[3, :] * cp.prod(coords_fine_gpu[:, np.newaxis], axis=2)
        + Z[4, :] * coords_fine_gpu[:, 0, None] ** 2
        + Z[5, :] * coords_fine_gpu[:, 1, None] ** 2
    )
    Zi_argmax_gpu = cp.argmax(Zi_fine, axis=0)
    Zi_argmax_x = cp.asnumpy(coords_fine_gpu[Zi_argmax_gpu, 0])
    Zi_argmax_y = cp.asnumpy(coords_fine_gpu[Zi_argmax_gpu, 1])
    coords_fine_gpu = None
    Zi_fine = None
    Z = None
    Zi_argmax_gpu = None
    del (
        Zi_fine,
        Z,
        Zi_argmax_gpu,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    return p2_rmse, Zi_argmax_x, Zi_argmax_y


def fit_poly2D_GPU_ar(coords, cc_gpu, coords_fine, nr_ar_splits=50):
    coords_gpu = cp.asarray(coords, dtype=cp.float32)
    # fitting second order polynomial
    A = cp.asarray(
        np.c_[
            np.ones(coords.shape[0]),
            coords[:, :2],
            np.prod(coords[:, :2], axis=1),
            coords[:, :2] ** 2,
        ],
        dtype=np.float32,
    )
    # cc_gpu = cp.asarray(corrcoef_ar, dtype=cp.float32)
    Z, _, _, _ = cp.linalg.lstsq(A, cc_gpu.T, rcond=None)
    Zi = (
        Z[0, :]
        + Z[1, :] * coords_gpu[:, 0, None]
        + Z[2, :] * coords_gpu[:, 1, None]
        + Z[3, :] * cp.prod(coords_gpu[:, cp.newaxis], axis=2)
        + Z[4, :] * coords_gpu[:, 0, None] ** 2
        + Z[5, :] * coords_gpu[:, 1, None] ** 2
    )
    dz_p2 = cc_gpu.T - Zi
    p2_rmse = cp.asnumpy(cp.sqrt(cp.mean(cp.square(dz_p2), axis=0)))
    # p2_iqr = cp.asnumpy(cp.percentile(dz_p2, [25, 75], axis=0) - cp.percentile(dz_p2, 25, axis=0))
    dz_p2 = None
    A = None
    cc_gpu = None
    coords_gpu = None
    Zi = None
    del A, cc_gpu, coords_gpu, Zi
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    #
    coords_fine_gpu = cp.asarray(coords_fine, dtype=cp.float32)
    Zi_argmax_gpu_x = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_argmax_gpu_x.fill(cp.nan)
    Zi_argmax_gpu_y = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_argmax_gpu_y.fill(cp.nan)
    # for ii in tqdm.tqdm(range(nr_ar_splits), desc='Calculating peaks'):
    for ii in range(nr_ar_splits):
        Z_cp_tile = cp.array_split(Z, nr_ar_splits, axis=1)[ii]
        Zi_fine = (
            Z_cp_tile[0, :]
            + Z_cp_tile[1, :] * coords_fine_gpu[:, 0, None]
            + Z_cp_tile[2, :] * coords_fine_gpu[:, 1, None]
            + Z_cp_tile[3, :] * cp.prod(coords_fine_gpu[:, np.newaxis], axis=2)
            + Z_cp_tile[4, :] * coords_fine_gpu[:, 0, None] ** 2
            + Z_cp_tile[5, :] * coords_fine_gpu[:, 1, None] ** 2
        )
        Zi_argmax_gpu = cp.argmax(Zi_fine, axis=0)
        Zi_argmax_gpu_x[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[Zi_argmax_gpu, 0]
        Zi_argmax_gpu_y[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[Zi_argmax_gpu, 1]
    Zi_argmax_gpu_x = cp.concatenate(Zi_argmax_gpu_x)
    Zi_argmax_gpu_x = Zi_argmax_gpu_x[~cp.isnan(Zi_argmax_gpu_x)]
    Zi_argmax_x = cp.asnumpy(Zi_argmax_gpu_x)
    Zi_argmax_gpu_y = cp.concatenate(Zi_argmax_gpu_y)
    Zi_argmax_gpu_y = Zi_argmax_gpu_y[~cp.isnan(Zi_argmax_gpu_y)]
    Zi_argmax_y = cp.asnumpy(Zi_argmax_gpu_y)
    Zi_argmax_gpu_x = None
    Zi_argmax_gpu_y = None
    coords_fine_gpu = None
    Z_cp_tile = None
    Zi_fine = None
    Z = None
    Zi_argmax_gpu = None
    del (
        Zi_argmax_gpu_x,
        Zi_argmax_gpu_y,
        coords_fine_gpu,
        Z_cp_tile,
        Zi_fine,
        Z,
        Zi_argmax_gpu,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    #
    # Numpy code
    # Z_np = cp.asnumpy(Z)
    # # create fine mesh for evaluating function
    # # Zi_fine = ( Z_np[0,:] + Z_np[1,:] * coords_fine[:,0, None] + Z_np[2,:] * coords_fine[:,1, None] +
    # #         Z_np[3,:] * np.prod(coords_fine[:,np.newaxis], axis=2) +
    # #         Z_np[4,:] * coords_fine[:,0, None]**2 +
    # #         Z_np[5,:] * coords_fine[:,1,None]**2 )
    # Zi_argmax_x = np.empty((nr_ar_splits, int(np.ceil(Z_np.shape[1]/nr_ar_splits))), dtype=np.float32)
    # Zi_argmax_x.fill(np.nan)
    # Zi_argmax_y = np.empty((nr_ar_splits, int(np.ceil(Z_np.shape[1]/nr_ar_splits))), dtype=np.float32)
    # Zi_argmax_y.fill(np.nan)
    # for ii in tqdm.tqdm(range(nr_ar_splits), desc='Calculating peaks'):
    #     Z_np_tile = np.array_split(Z_np, nr_ar_splits, axis=1)[ii]
    #     Zi_fine = ( Z_np_tile[0,:] + Z_np_tile[1,:] * coords_fine[:,0, None] + Z_np_tile[2,:] * coords_fine[:,1, None] +
    #             Z_np_tile[3,:] * np.prod(coords_fine[:,np.newaxis], axis=2) +
    #             Z_np_tile[4,:] * coords_fine[:,0, None]**2 +
    #             Z_np_tile[5,:] * coords_fine[:,1,None]**2 )
    #     Zi_argmax = np.argmax(Zi_fine, axis=0)
    #     Zi_argmax_x[ii,0:Z_np_tile.shape[1]] = coords_fine[Zi_argmax,0]
    #     Zi_argmax_y[ii,0:Z_np_tile.shape[1]] = coords_fine[Zi_argmax,1]
    # Zi_argmax_x = np.concatenate(Zi_argmax_x)
    # Zi_argmax_x = Zi_argmax_x[~np.isnan(Zi_argmax_x)]
    # Zi_argmax_y = np.concatenate(Zi_argmax_y)
    # Zi_argmax_y = Zi_argmax_y[~np.isnan(Zi_argmax_y)]
    return p2_rmse, Zi_argmax_x, Zi_argmax_y


def fit_poly2D_ar(coords, corrcoef_ar, coords_fine):
    # fitting second order polynomial
    A = np.c_[
        np.ones(coords.shape[0]),
        coords[:, :2],
        np.prod(coords[:, :2], axis=1),
        coords[:, :2] ** 2,
    ]
    Z, _, _, _ = np.linalg.lstsq(A, corrcoef_ar.T, rcond=None)
    Zi = (
        Z[0, :]
        + Z[1, :] * coords[:, 0, None]
        + Z[2, :] * coords[:, 1, None]
        + Z[3, :] * np.prod(coords[:, np.newaxis], axis=2)
        + Z[4, :] * coords[:, 0, None] ** 2
        + Z[5, :] * coords[:, 1, None] ** 2
    )
    dz_p2 = corrcoef_ar.T - Zi
    p2_rmse = np.float32(np.sqrt(np.mean(np.square(dz_p2), axis=0)))
    p2_iqr = np.float32(
        np.percentile(dz_p2, 75, axis=0) - np.percentile(dz_p2, 25, axis=0)
    )
    # create fine mesh for evaluating function
    Zi_fine = (
        Z[0, :]
        + Z[1, :] * coords_fine[:, 0, None]
        + Z[2, :] * coords_fine[:, 1, None]
        + Z[3, :] * np.prod(coords_fine[:, np.newaxis], axis=2)
        + Z[4, :] * coords_fine[:, 0, None] ** 2
        + Z[5, :] * coords_fine[:, 1, None] ** 2
    )
    Zi_argmax = np.argmax(Zi_fine, axis=0)
    Zi_argmax_x = coords_fine[Zi_argmax, 0]
    Zi_argmax_y = coords_fine[Zi_argmax, 1]
    return p2_rmse, p2_iqr, Zi_fine, Zi_argmax_x, Zi_argmax_y


def pearsonr_2D(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    upper = np.sum((x - np.mean(x)) * (y - np.mean(y, axis=1)[:, None]), axis=1)
    lower = np.sqrt(
        np.sum(np.power(x - np.mean(x), 2))
        * np.sum(np.power(y - np.mean(y, axis=1)[:, None], 2), axis=1)
    )
    rho = upper / lower
    return rho


def pearsonr_2D_array_cupy(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = cp.empty((x.shape[0], y.shape[2]), dtype=np.float32)
    rho.fill(cp.nan)
    for i in range(x.shape[0]):
        x_ = x[i, :]
        y_ = y[i, :, :].T
        upper = cp.sum(
            (x_ - cp.mean(x_)) * (y_ - cp.mean(y_, axis=1)[:, None]),
            axis=1,
        )
        lower = cp.sqrt(
            cp.sum(cp.power(x_ - cp.mean(x_), 2))
            * cp.sum(cp.power(y_ - cp.mean(y_, axis=1)[:, None], 2), axis=1)
        )
        rho[i] = upper / lower
    return rho


def pearsonr_2D_array(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = np.empty((x.shape[0], y.shape[2]), dtype=np.float32)
    rho.fill(np.nan)
    for i in tqdm.tqdm(range(x.shape[0])):
        x_ = x[i, :]
        y_ = y[i, :, :].T
        upper = np.sum(
            (x_ - np.mean(x_)) * (y_ - np.mean(y_, axis=1)[:, None]),
            axis=1,
        )
        lower = np.sqrt(
            np.sum(np.power(x_ - np.mean(x_), 2))
            * np.sum(np.power(y_ - np.mean(y_, axis=1)[:, None], 2), axis=1)
        )
        rho[i] = upper / lower
    return rho


def pearsonr_corrcoef_2D(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = np.empty((x.shape[0], y.shape[2]), dtype=np.float32)
    rho.fill(np.nan)
    for i in range(x.shape[0]):
        if np.count_nonzero(x[i, :]) == 0:
            continue
        rho[i] = np.corrcoef(x[i, :], y[i, :, :].T, dtype=np.float32)[1:, 0]
    return rho


@nb.njit(parallel=True)
def pearsonr_2D_numba(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = np.empty((x.shape[0], y.shape[2]), dtype=np.float32)
    rho.fill(np.nan)
    for i in nb.prange(x.shape[0]):
        if np.count_nonzero(x[i, :]):
            continue
        rho[i] = np.corrcoef(x[i, :], y[i, :, :].T)[1:, 0]
    return rho


if __name__ == "__main__":
    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching.py \
    #   /work/bookhage/Landsat/P231R078/corr_dates_sd1_cc20 \
    #   /work/bookhage/Landsat/P231R078/run_block_matching_231078_os05_bs121_sr08_ms05.bash \
    #   231078 121 8 5 5 2 \
    #   /work/bookhage/Landsat/P231R078/CORR_os05_bs121_sr08_ms05

    # fname1 = sys.argv[1]
    # fname2 = sys.argv[2]
    # block_size = int(sys.argv[3])
    # search_radius = int(sys.argv[4])
    # oversampling = int(sys.argv[5])
    # matching_step = int(sys.argv[6])
    # cudadevice = int(sys.argv[7])
    # tifdirname = sys.argv[8]
    # nthreads_exp = 9

    fname1 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    # fname2 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    fname2 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05/LC08_L1TP_231076_20230715_20230724_02_T1_B8.TIF"
    # fname1 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20230715_20230724_02_T1_B8.TIF"
    block_size = 91
    search_radius = 15
    cudadevice = 0
    oversampling = 5
    matching_step = 1
    # tifdirname = "/work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr15_ms05_fullC"
    # maskfname = "/work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc30_B_median_velocity_magnitude_my_gf_cc1e4m2_filt_os05.tif"
    tifdirname = "/raid2-gpu2/bodo/LANDSAT/P231R076/CORR_os05_bs91_sr15_ms05_fullC"
    maskfname = "/raid2-gpu2/bodo/LANDSAT/P231R076/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc30_B_median_velocity_magnitude_my_gf_cc1e4m2_filt_os05.tif"
    nthreads_exp = 9
    max_order = 4
    Landsat_mask_exists = True

    # fname1 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    # block_size = 91
    # search_radius = 15
    # cudadevice = 0
    # oversampling = 5
    # matching_step = 1
    # tifdirname ='/work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr15_ms05'

    #
    # cuda.select_device(cudadevice)
    # logging.info("Using CUDA Device %d" % cudadevice)
    logging.info("Loading Landsat TIFs: %s and %s" % (fname1, fname2))
    start0 = time.time()
    Landsat_B8_1, Landsat_1_ds_gt, Landsat_1_ds_proj, epsg_code = load_Landsat_tif(
        fname1
    )
    Landsat_B8_2, Landsat_2_ds_gt, Landsat_2_ds_proj, epsg_code = load_Landsat_tif(
        fname2
    )
    end = time.time()
    length_s = end - start0
    logging.info(
        "Loading Landsat data took %d seconds or %2.2f minutes"
        % (length_s, length_s / 60)
    )

    logging.info("Loading mask %s" % maskfname)
    start0 = time.time()
    Landsat_mask, Landsat_mask_ds_gt, Landsat_mask_ds_proj, epsg_code = load_mask_tif(
        maskfname
    )
    end = time.time()
    length_s = end - start0
    logging.info(
        "Loading mask took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    )

    logging.info(
        "Size Landsat 1: %d x %d" % (Landsat_B8_1.shape[0], Landsat_B8_1.shape[1])
    )
    logging.info(
        "Size Landsat 2: %d x %d" % (Landsat_B8_2.shape[0], Landsat_B8_2.shape[1])
    )
    logging.info(
        "Size mask     : %d x %d" % (Landsat_mask.shape[0], Landsat_mask.shape[1])
    )
    if Landsat_B8_1.shape != Landsat_mask.shape:
        logging.info("Landsat TIF 1 and mask array have different dimensions.")

    # creating coordinates for fitting. Make sure to flip Y-axes coordinates
    sr_coordx, sr_coordy = np.meshgrid(
        np.arange(
            0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]
        ),
        np.arange(
            0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]
        ),
    )
    sr_coordx = sr_coordx.ravel() - np.max(sr_coordx) / 2
    sr_coordy = np.flipud(sr_coordy.ravel()) - np.max(sr_coordy) / 2
    coords = np.c_[sr_coordx, sr_coordy]
    basis = get_basis(coords[:, 0], coords[:, 1], max_order)
    coord_upsampling_factor = 10
    # sr_coordx_fine, sr_coordy_fine = np.meshgrid(
    #     np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    #     np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    # )
    sr_coordx_fine, sr_coordy_fine = np.meshgrid(
        np.arange(
            0,
            np.max(coords[:, 0])
            + np.max(sr_coordx)
            + Landsat_1_ds_gt[1] / coord_upsampling_factor,
            Landsat_1_ds_gt[1] / coord_upsampling_factor,
        ),
        np.arange(
            0,
            np.max(coords[:, 0])
            + np.max(sr_coordx)
            + Landsat_1_ds_gt[1] / coord_upsampling_factor,
            Landsat_1_ds_gt[1] / coord_upsampling_factor,
        ),
    )
    sr_coordx_fine = sr_coordx_fine.ravel() - np.max(sr_coordx_fine) / 2
    sr_coordy_fine = np.flipud(sr_coordy_fine.ravel()) - np.max(sr_coordy_fine) / 2
    Xmin_fine = np.min(sr_coordx_fine)
    Xmax_fine = np.max(sr_coordx_fine)
    Ymin_fine = np.min(sr_coordy_fine)
    Ymax_fine = np.max(sr_coordy_fine)
    coords_fine = np.c_[sr_coordx_fine, sr_coordy_fine]

    year_name1 = os.path.basename(fname1).split("_")[3]
    year_name2 = os.path.basename(fname2).split("_")[3]
    fname = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d" % (
        year_name1,
        year_name2,
        oversampling,
        block_size,
        search_radius,
        matching_step,
    )

    dirname = "%s_%s_os%02d" % (year_name1, year_name2, oversampling)
    geotiff_fn_u = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_u.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    geotiff_fn_v = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_v.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    geotiff_fn_c = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_c.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )

    if (
        os.path.exists(geotiff_fn_u)
        and os.path.exists(geotiff_fn_v)
        and os.path.exists(geotiff_fn_c)
    ):
        logging.info(
            "Files exists: %s, %s, %s" % (geotiff_fn_u, geotiff_fn_v, geotiff_fn_c)
        )
        logging.info("exit")
        exit()

    if not os.path.exists(tifdirname):
        os.mkdir(tifdirname)

    # if not os.path.exists(dirname):
    #     os.mkdir(dirname)
    if matching_step != 1:
        logging.info("Masking skip steps with matching step of %02d" % matching_step)
        # apply skip stepsize
        # find center point: matching_step = 3, one step in and then in 3 steps
        Landsat_B8_mask = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        if matching_step == 3:
            Landsat_B8_mask[1::matching_step, 1::matching_step] = 0
        elif matching_step == 5:
            Landsat_B8_mask[2::matching_step, 2::matching_step] = 0
        elif matching_step == 7:
            Landsat_B8_mask[3::matching_step, 3::matching_step] = 0
        elif matching_step == 9:
            Landsat_B8_mask[4::matching_step, 4::matching_step] = 0

        # make sure to mask out nan area surrounding Landsat image
        Landsat_B8_mask[Landsat_B8_1 == 0] = 1
        nr_nan_pixels1 = np.count_nonzero(Landsat_B8_mask)
        # nr_nan_pixels1 = len(np.where(Landsat_B8_mask == 1)[0])
        logging.info(
            "Masked %s nan pixels (%2.1f %%)"
            % (
                f"{nr_nan_pixels1:,}",
                nr_nan_pixels1 / (Landsat_B8_1.shape[0] * Landsat_B8_1.shape[1]) * 100,
            )
        )
    elif matching_step == 1:
        logging.info("Creating mask for nan areas")
        Landsat_B8_mask = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        # all areas that not 0 (above 0) are set to 0 in the mask - these are processed
        # all values with 1 are masked out
        # we first set all values from the border to 1
        if Landsat_mask_exists == False:
            Landsat_B8_mask[Landsat_B8_1 != 0] = 0
        elif Landsat_mask_exists == True:
            # next, we set all bbox areas from mask file to 0 (they will be processed)
            Landsat_B8_mask[Landsat_mask == 1] = 0
        nr_nan_pixels1 = np.count_nonzero(Landsat_B8_mask == 1)
        logging.info(
            "Masked %s nan pixels (%2.1f %%)"
            % (
                f"{nr_nan_pixels1:,}",
                nr_nan_pixels1 / (Landsat_B8_1.shape[0] * Landsat_B8_1.shape[1]) * 100,
            )
        )

    nr_of_correlation_pixels = np.count_nonzero(Landsat_B8_mask == 0)
    logging.info(
        "Running correlation for %s pixels (%02.1f %%)"
        % (
            f"{nr_of_correlation_pixels:,}",
            nr_of_correlation_pixels
            / (Landsat_B8_mask.shape[0] * Landsat_B8_mask.shape[1])
            * 100,
        )
    )

    # logging.info("Extract geotiff information from %s" % (fname1))
    # gt, proj, epsg_code, ys, xs = get_geotiff_info(fname1)

    half_block_size = block_size / 2
    hbs = int(half_block_size)
    bs = 2 * hbs + 1
    H, W = Landsat_B8_1.shape
    # Pad so that every pixel center is valid:
    pad_mode = "reflect"
    img1p = np.pad(Landsat_B8_1, ((hbs, hbs), (hbs, hbs)), mode=pad_mode)
    img2p = np.pad(
        Landsat_B8_2,
        (
            (hbs + search_radius, hbs + search_radius),
            (hbs + search_radius, hbs + search_radius),
        ),
        mode=pad_mode,
    )
    # All candidate patches in img2 (including extra R border)
    cand_patches = sliding_window_view(img2p, (bs, bs))
    # Landsat_B8_mask = np.zeros(Landsat_B8_1.shape, dtype=np.bool_)
    # step_skip = 2
    # Landsat_B8_mask[2 :: matching_step * step_skip, 2 :: matching_step * step_skip] = 1
    # Process each landslide mask separately
    Landsat_B8_mask_label = measure.label(Landsat_B8_mask, background=1)
    nr_labels = np.max(Landsat_B8_mask_label)

    # Prepare arrays for for loop
    p2_rmse_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    p2_rmse_ar.fill(np.nan)
    Zi_p2_x_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    Zi_p2_x_ar.fill(np.nan)
    Zi_p2_y_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    Zi_p2_y_ar.fill(np.nan)
    # p4_rmse_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    # p4_rmse_ar.fill(np.nan)
    # Zi_p4_x_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    # Zi_p4_x_ar.fill(np.nan)
    # Zi_p4_y_ar = np.empty(Landsat_B8_mask.shape, dtype=np.float32)
    # Zi_p4_y_ar.fill(np.nan)
    A = cp.asarray(
        np.c_[
            np.ones(coords.shape[0]),
            coords[:, :2],
            np.prod(coords[:, :2], axis=1),
            coords[:, :2] ** 2,
        ],
        dtype=np.float32,
    )
    coords_fine_gpu = cp.asarray(coords_fine)
    coords_gpu = cp.asarray(coords)
    # basis = get_basis(coords[:, 0], coords[:, 1], max_order)
    # # fitting nth-order polynomial
    # A4 = cp.asarray(np.vstack(basis).T, dtype=cp.float32)
    # B = cp.asarray(
    #     get_basis(coords[:, 0], coords[:, 1], max_order), dtype=np.float32
    # ).reshape(len(basis), coords_gpu.shape[0])
    # B_fine = cp.array(
    #     get_basis(coords_fine[:, 0], coords_fine[:, 1], max_order), dtype=cp.float32
    # ).reshape(len(basis), coords_fine.shape[0])

    logging.info("Iterate through all %d labels" % nr_labels)
    start = time.time()
    for i in tqdm.tqdm(range(1, nr_labels), desc="Iterating through labels"):
        # Start at 1 because 0 is background label
        clabel = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        clabel[Landsat_B8_mask_label == i] = 0
        if np.count_nonzero(clabel == 0) > 1000:
            logging.info("i: %04d has %d pixels" % (i, np.count_nonzero(clabel == 0)))
            continue
        # Patches centered at every original pixel
        ref_patches = sliding_window_view(img1p, (bs, bs))[~clabel, :, :]
        ref_patches = ref_patches.reshape(
            ref_patches.shape[0], ref_patches.shape[1] * ref_patches.shape[2]
        )
        # For each (y, x), collect candidate patches in a (2R+1)x(2R+1) window
        disp_view = sliding_window_view(
            cand_patches,
            window_shape=(2 * search_radius + 1, 2 * search_radius + 1),
            axis=(0, 1),
        )[~clabel, :, :, :, :]
        disp_view = disp_view.reshape(
            disp_view.shape[0],
            disp_view.shape[1] * disp_view.shape[2],
            disp_view.shape[3] * disp_view.shape[4],
        )
        # CC_ar = pearsonr_2D_array(ref_patches, disp_view)
        CC_ar = pearsonr_2D_array_cupy(
            cp.asarray(ref_patches, dtype=cp.float32), cp.asarray(disp_view, cp.float32)
        )
        ref_patches = None
        disp_view = None
        del ref_patches, disp_view
        mempool.free_all_blocks()
        pinned_mempool.free_all_blocks()
        p2_rmse, Zi_p2_x, Zi_p2_y = fit_poly2D_cupy_ar(
            A, coords_gpu, CC_ar, coords_fine_gpu
        )
        idxs = np.argwhere(Landsat_B8_mask_label == i)
        p2_rmse_ar[idxs[:, 0], idxs[:, 1]] = p2_rmse
        Zi_p2_x_ar[idxs[:, 0], idxs[:, 1]] = Zi_p2_x
        Zi_p2_y_ar[idxs[:, 0], idxs[:, 1]] = Zi_p2_y
        # p4_rmse, Zi_p4_x, Zi_p4_y = fit_polynD_cupy_ar(
        #     A4, B, B_fine, CC_ar, coords_fine_gpu
        # )
        # p4_rmse_ar[idxs[:, 0], idxs[:, 1]] = p4_rmse
        # Zi_p4_x_ar[idxs[:, 0], idxs[:, 1]] = Zi_p4_x
        # Zi_p4_y_ar[idxs[:, 0], idxs[:, 1]] = Zi_p4_y
        CC_ar = None
        del CC_ar
        mempool.free_all_blocks()
        pinned_mempool.free_all_blocks()

    end = time.time()
    length_s = end - start
    logging.info(
        "All patches took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_mask.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_mask_geotiff(
        geotiff_fn, Landsat_B8_mask, epsg_code, geotransform=Landsat_1_ds_gt
    )

    logging.info("Creating empty arrays to store peak-fitting results")
    p2_rmse_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    p2_rmse_ar.fill(np.nan)
    Zi_p2_x_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_p2_x_ar.fill(np.nan)
    Zi_p2_y_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_p2_y_ar.fill(np.nan)
    p4_rmse_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    p4_rmse_ar.fill(np.nan)
    Zi_p4_x_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_p4_x_ar.fill(np.nan)
    Zi_p4_y_ar = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_p4_y_ar.fill(np.nan)
    u_ar = np.zeros(Landsat_B8_1.shape, dtype=np.int8)
    v_ar = np.zeros(Landsat_B8_1.shape, dtype=np.int8)

    logging.info(
        "Running block matching for %s and %s with block size: %02d and search radius %02d and matching step %02d and nthreads_exp %02d"
        % (fname1, fname2, block_size, search_radius, matching_step, nthreads_exp)
    )
    # tilex_start = 50000
    # tilex_end = tilex_start + tilesize
    # tiley_start = 50000
    # tiley_end = tiley_start + tilesize
    # set tiling coordinates
    tilefsize_x, tilefsize_y = Landsat_B8_1.shape
    window_size = block_size
    tilesize = 5000
    nr_tilex = int(np.ceil(tilefsize_x / tilesize))
    nr_tiley = int(np.ceil(tilefsize_y / tilesize))
    tilex_start_list = []
    tilex_end_list = []
    tiley_start_list = []
    tiley_end_list = []
    start_all = time.time()
    for ii in range(nr_tilex):
        for jj in range(nr_tiley):
            logging.info(
                "Running Tile (%01d/%01d:%01d/%01d)" % (ii, nr_tilex, jj, nr_tiley)
            )
            if ii == 0:
                tilex_start = 0
                tilex_end = tilex_start + tilesize + window_size
                tilex_start_nw = 0
                tilex_end_nw = tilex_start + tilesize
                tilex_start_nwc = 0
                tilex_end_nwc = tilex_end - window_size
            elif (ii > 0) and (ii < nr_tiley):
                tilex_start = tilesize * ii - window_size
                tilex_end = tilex_start + tilesize + window_size + window_size
                tilex_start_nw = tilesize * ii
                tilex_end_nw = tilex_start + tilesize + window_size
                tilex_start_nwc = window_size
                tilex_end_nwc = tilesize + window_size
            elif ii == nr_tiley:
                tilex_start = tilesize * ii - window_size
                tilex_end = tilefsize_x
                tilex_start_nw = tilesize * ii
                tilex_end_nw = tilex_end
                tilex_start_nwc = window_size
                tilex_end_nwc = tilefsize_x
            if jj == 0:
                tiley_start = 0
                tiley_end = tiley_start + tilesize + window_size
                tiley_start_nw = 0
                tiley_end_nw = tiley_start + tilesize
                tiley_start_nwc = 0
                tiley_end_nwc = tiley_end - window_size
            elif (jj > 0) and (jj < nr_tiley):
                tiley_start = tilesize * jj - window_size
                tiley_end = tiley_start + tilesize + window_size + window_size
                tiley_start_nw = tilesize * jj
                tiley_end_nw = tiley_start + tilesize + window_size
                tiley_start_nwc = window_size
                tiley_end_nwc = tilesize + window_size
            elif jj == nr_tiley:
                tiley_start = tilesize * jj - window_size
                tiley_end = tilefsize_y
                tiley_start_nw = tilesize * jj
                tiley_end_nw = tiley_end
                tiley_start_nwc = window_size
                tiley_end_nwc = tilefsize_y
            # tilex_start_list.append(tilex_start)
            # tilex_end_list.append(tilex_end)
            # tiley_start_list.append(tiley_start)
            # tiley_end_list.append(tiley_end)
            # start = time.time()
            # u, v, correlation = block_matching_masked_ncc_uint_nonzero(
            #     Landsat_B8_1[tilex_start:tilex_end, tiley_start:tiley_end],
            #     Landsat_B8_2[tilex_start:tilex_end, tiley_start:tiley_end],
            #     Landsat_B8_mask[tilex_start:tilex_end, tiley_start:tiley_end],
            #     block_size,
            #     search_radius,
            #     nthreads_exp=nthreads_exp,
            # )
            # end = time.time()
            # length_s = end - start
            # logging.info(
            #     "Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
            # )
            # start = time.time()
            u, v, correlation = block_matching_masked_ncc_uint_nonzero_fullc(
                Landsat_B8_1[tilex_start:tilex_end, tiley_start:tiley_end],
                Landsat_B8_2[tilex_start:tilex_end, tiley_start:tiley_end],
                Landsat_B8_mask[tilex_start:tilex_end, tiley_start:tiley_end],
                block_size,
                search_radius,
                nthreads_exp=nthreads_exp,
            )
            # end = time.time()
            # length_s = end - start
            # logging.info(
            #     "Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
            # )
            #
            logging.info("Converting correlation array")
            # find rows that are not all 0
            idx2run = np.where(
                np.count_nonzero(correlation, axis=(2, 3)).reshape(-1)
                == ((search_radius * 2 + 1) * (search_radius * 2 + 1))
            )[0]
            logging.info(
                "Found %s pixels out of %s with valid correlation matrix values"
                % (
                    f"{len(idx2run):,}",
                    f"{correlation.shape[0] * correlation.shape[1]:,}",
                )
            )
            corrcoef_ar = (
                correlation.reshape(
                    correlation.shape[0] * correlation.shape[1],
                    correlation.shape[2] * correlation.shape[3],
                )[idx2run]
                / 127
            )
            logging.info(
                "Calculating max. values for fitted peaks for %s correlation arrays"
                % (f"{len(idx2run):,}")
            )
            start = time.time()
            p2_rmse, Zi_p2_x, Zi_p2_y = fit_poly2D_GPU_ar(
                coords, corrcoef_ar, coords_fine
            )
            end = time.time()
            length_s = end - start
            logging.info(
                "Polynomial function of 2nd order: Calculation took %d seconds or %2.2f minutes"
                % (length_s, length_s / 60)
            )
            # start = time.time()
            # p2_log_rmse, Zi_p2_log_x, Zi_p2_log_y = fit_poly2D_GPU_ar(
            #     coords, np.log(corrcoef_ar), coords_fine
            # )
            # end = time.time()
            # length_s = end - start
            # logging.info(
            #     "Polynomial log function of 2nd order: Calculation took %d seconds or %2.2f minutes"
            #     % (length_s, length_s / 60)
            # )
            start = time.time()
            p4_rmse, Zi_p4_x, Zi_p4_y = fit_polynD_GPU_ar(
                coords,
                corrcoef_ar,
                coords_fine,
                max_order=4,
                nr_ar_splits=1000,
            )
            end = time.time()
            length_s = end - start
            logging.info(
                "Polynomial function of 4th order: Calculation took %d seconds or %2.2f minutes"
                % (length_s, length_s / 60)
            )
            corrcoef_ar = None
            correlation = None
            del corrcoef_ar, correlation
            #
            p2_rmse_2D = np.empty(u.shape, dtype=np.float32)
            p2_rmse_2D.fill(np.nan)
            p2_rmse_2D.reshape(-1)[idx2run] = p2_rmse
            p2_rmse_2D = p2_rmse_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            p2_rmse_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                p2_rmse_2D
            )
            del p2_rmse_2D, p2_rmse
            Zi_argmax_x_2D = np.empty(u.shape, dtype=np.float32)
            Zi_argmax_x_2D.fill(np.nan)
            Zi_argmax_x_2D.reshape(-1)[idx2run] = Zi_p2_x
            Zi_argmax_x_2D = Zi_argmax_x_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            Zi_p2_x_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                Zi_argmax_x_2D - sr_coordx_fine0
            )
            del Zi_argmax_x_2D, Zi_p2_x
            #
            Zi_argmax_y_2D = np.empty(u.shape, dtype=np.float32)
            Zi_argmax_y_2D.fill(np.nan)
            Zi_argmax_y_2D.reshape(-1)[idx2run] = Zi_p2_y
            Zi_argmax_y_2D = Zi_argmax_y_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            Zi_p2_y_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                Zi_argmax_y_2D - sr_coordy_fine0
            )
            del Zi_argmax_y_2D, Zi_p2_y
            #
            p4_rmse_2D = np.empty(u.shape, dtype=np.float32)
            p4_rmse_2D.fill(np.nan)
            p4_rmse_2D.reshape(-1)[idx2run] = p4_rmse
            p4_rmse_2D = p4_rmse_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            p4_rmse_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                p4_rmse_2D
            )
            del p4_rmse_2D, p4_rmse
            Zi_argmax_x_2D = np.empty(u.shape, dtype=np.float32)
            Zi_argmax_x_2D.fill(np.nan)
            Zi_argmax_x_2D.reshape(-1)[idx2run] = Zi_p4_x
            Zi_argmax_x_2D = Zi_argmax_x_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            Zi_p4_x_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                Zi_argmax_x_2D - sr_coordx_fine0
            )
            del Zi_argmax_x_2D, Zi_p4_x
            #
            Zi_argmax_y_2D = np.empty(u.shape, dtype=np.float32)
            Zi_argmax_y_2D.fill(np.nan)
            Zi_argmax_y_2D.reshape(-1)[idx2run] = Zi_p4_y
            Zi_argmax_y_2D = Zi_argmax_y_2D[
                tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc
            ]
            Zi_p4_y_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = (
                Zi_argmax_y_2D - sr_coordy_fine0
            )
            del Zi_argmax_y_2D, Zi_p4_y
            #
            u_2D = np.zeros(u.shape, dtype=np.int8)
            u_2D.reshape(-1)[idx2run] = u.ravel()[idx2run]
            u_2D = u_2D[tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc]
            u_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = u_2D
            del u_2D, u
            #
            v_2D = np.zeros(v.shape, dtype=np.int8)
            v_2D.reshape(-1)[idx2run] = v.ravel()[idx2run]
            v_2D = v_2D[tilex_start_nwc:tilex_end_nwc, tiley_start_nwc:tiley_end_nwc]
            v_ar[tilex_start_nw:tilex_end_nw, tiley_start_nw:tiley_end_nw] = v_2D
            del v_2D, v
        end = time.time()
        length_s = end - start_all
        logging.info(
            "All tiles processing: Calculation took %d seconds or %2.2f minutes"
            % (length_s, length_s / 60)
        )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_u.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(
        geotiff_fn,
        u_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_v.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(geotiff_fn, v_ar, int(epsg_code), geotransform=Landsat_1_ds_gt)

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p2_rmse.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        p2_rmse_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p2_x.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        Zi_p2_x_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p2_y.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        Zi_p2_y_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p4_rmse.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        p4_rmse_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p4_x.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        Zi_p4_x_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_p4_y.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        Zi_p4_y_ar,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )

    # start = time.time()
    # save_all_geotiff(tifdirname)
    # end = time.time()
    # length_s = end - start
    # logging.info(
    #     "Writing all tiles took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    # )
    end = time.time()

    length_s = end - start0
    logging.info(
        "All steps combined took %d seconds or %2.2f minutes or %2.2f hours "
        % (length_s, length_s / 60, length_s / (60 * 60))
    )
