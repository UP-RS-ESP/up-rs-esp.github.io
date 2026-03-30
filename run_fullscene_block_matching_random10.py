import numpy as np
import numba as nb
from numba import cuda
from math import sqrt
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, tqdm
import matplotlib.pyplot as plt
import scipy.optimize
from numpy.lib.stride_tricks import sliding_window_view


gdal.UseExceptions()

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
    # Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint16")
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


def Gaussian2D(xy, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    x, y = xy
    xo = float(xo)
    yo = float(yo)
    a = (np.cos(theta) ** 2) / (2 * sigma_x**2) + (np.sin(theta) ** 2) / (
        2 * sigma_y**2
    )
    b = -(np.sin(2 * theta)) / (4 * sigma_x**2) + (np.sin(2 * theta)) / (4 * sigma_y**2)
    c = (np.sin(theta) ** 2) / (2 * sigma_x**2) + (np.cos(theta) ** 2) / (
        2 * sigma_y**2
    )
    g = offset + amplitude * np.exp(
        -(a * ((x - xo) ** 2) + 2 * b * (x - xo) * (y - yo) + c * ((y - yo) ** 2))
    )
    return g.ravel()


def pearsonr_2D_array(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = np.empty((x.shape[0], y.shape[1]), dtype=np.float32)
    rho.fill(np.nan)
    for i in tqdm.tqdm(range(x.shape[0])):
        upper = np.sum(
            (x[i, :] - np.mean(x[i, :]))
            * (y[i, :] - np.mean(y[i, :], axis=1)[:, None]),
            axis=1,
        )
        lower = np.sqrt(
            np.sum(np.power(x[i, :] - np.mean(x[i, :]), 2))
            * np.sum(np.power(y[i, :] - np.mean(y[i, :], axis=1)[:, None], 2), axis=1)
        )
        rho[i] = upper / lower
    return rho


@nb.njit(parallel=True)
def pearsonr_2D_numba(x, y):
    """computes pearson correlation coefficient
    where x is a 1D and y a 2D array"""
    rho = np.empty((x.shape[0], y.shape[1]), dtype=np.float32)
    rho.fill(np.nan)
    for i in nb.prange(x.shape[0]):
        rho[i] = np.corrcoef(x[i, :], y[i, :, :])[1:, 0]
    return rho


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


def plot_cc_fits(
    ref_img,
    corrcoef_img,
    corrcoef_p2_img,
    corrcoef_p8_img,
    corrcoef_G2D_img,
    CC_argmax_x,
    CC_argmax_y,
    Zi_argmax_x,
    Zi_argmax_y,
    Zi_p8_argmax_x,
    Zi_p8_argmax_y,
    G2D_fit_fine_argmax_x,
    G2D_fit_fine_argmax_y,
    p2_rmse,
    p2_iqr,
    G2D_rmse,
    G2D_iqr,
    fig_title,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=1, ncols=5, figsize=(16, 6), dpi=300, layout="constrained"
    )
    im0 = ax[0].imshow(
        ref_img,
        interpolation="nearest",
        vmin=np.nanpercentile(ref_img, 2),
        vmax=np.nanpercentile(ref_img, 98),
        cmap="gray",
    )
    ax[0].get_xaxis().set_ticks([])
    ax[0].get_yaxis().set_ticks([])
    ax[0].set_title(
        "Landsat Reference Image (%d x %d)" % (ref_img.shape[0], ref_img.shape[1])
    )
    h = plt.colorbar(im0, ax=ax[0], orientation="horizontal", shrink=0.8)
    h.set_label("Landsat Grayscale", fontsize=14)
    im1 = ax[1].imshow(
        corrcoef_img,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    ax[1].plot(
        CC_argmax_x, CC_argmax_y, "k+", ms=5, label="max. value from orig.matrix"
    )
    ax[1].plot(
        Zi_argmax_x, Zi_argmax_y, "o", color="gray", ms=5, label="2nd order polynomial"
    )
    ax[1].plot(
        Zi_p8_argmax_x,
        Zi_p8_argmax_y,
        "o",
        color="steelblue",
        ms=5,
        label="4th order polynomial",
    )
    ax[1].plot(
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
        "o",
        color="black",
        ms=5,
        label="2D Gaussian fit",
    )
    ax[1].get_xaxis().set_ticks([])
    ax[1].get_yaxis().set_ticks([])
    ax[1].set_title(
        "Original CC (%d x %d)" % (corrcoef_img.shape[0], corrcoef_img.shape[1])
    )
    im2 = ax[2].imshow(
        corrcoef_p2_img,
        interpolation="nearest",
        extent=[Xmin_fine, Xmax_fine, Ymin_fine, Ymax_fine],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    ax[2].plot(
        CC_argmax_x, CC_argmax_y, "k+", ms=5, label="max. value from orig.matrix"
    )
    ax[2].plot(
        Zi_argmax_x, Zi_argmax_y, "o", color="gray", ms=5, label="2nd order polynomial"
    )
    ax[2].plot(
        Zi_p8_argmax_x,
        Zi_p8_argmax_y,
        "o",
        color="steelblue",
        ms=5,
        label="4th order polynomial",
    )
    ax[2].plot(
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
        "o",
        color="black",
        ms=5,
        label="2D Gaussian fit",
    )
    ax[2].get_xaxis().set_ticks([])
    ax[2].get_yaxis().set_ticks([])
    ax[2].set_title(
        "2nd order polynomial CC"
        + "\n"
        + "RMSE: %2.3f, IQR: %2.3f (%d x %d)"
        % (p2_rmse, p2_iqr, corrcoef_p2_img.shape[0], corrcoef_p2_img.shape[1])
    )
    im3 = ax[3].imshow(
        corrcoef_p8_img,
        interpolation="nearest",
        extent=[Xmin_fine, Xmax_fine, Ymin_fine, Ymax_fine],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    ax[3].plot(
        CC_argmax_x, CC_argmax_y, "k+", ms=5, label="max. value from orig.matrix"
    )
    ax[3].plot(
        Zi_argmax_x, Zi_argmax_y, "o", color="gray", ms=5, label="2nd order polynomial"
    )
    ax[3].plot(
        Zi_p8_argmax_x,
        Zi_p8_argmax_y,
        "o",
        color="steelblue",
        ms=5,
        label="4th order polynomial",
    )
    ax[3].plot(
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
        "o",
        color="black",
        ms=5,
        label="2D Gaussian fit",
    )
    ax[3].get_xaxis().set_ticks([])
    ax[3].get_yaxis().set_ticks([])
    ax[3].set_title(
        "4th order polynomial CC"
        + "\n"
        + "RMSE: %2.3f, IQR: %2.3f (%d x %d)"
        % (p8_rmse, p8_iqr, corrcoef_p8_img.shape[0], corrcoef_p8_img.shape[1])
    )
    im4 = ax[4].imshow(
        corrcoef_G2D_img,
        interpolation="nearest",
        extent=[Xmin_fine, Xmax_fine, Ymin_fine, Ymax_fine],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    h = plt.colorbar(im4, ax=ax[1:], orientation="horizontal", shrink=0.8)
    h.set_label("Pearson Correlation Coefficient", fontsize=14)
    ax[4].plot(
        CC_argmax_x,
        CC_argmax_y,
        "k+",
        ms=5,
        label="max. value from orig.matrix (%2.2f, %2.2f)" % (CC_argmax_x, CC_argmax_y),
    )
    ax[4].plot(
        Zi_argmax_x,
        Zi_argmax_y,
        "o",
        color="gray",
        ms=5,
        label="2nd order polynomial (%2.2f, %2.2f)" % (Zi_argmax_x, Zi_argmax_y),
    )
    ax[4].plot(
        Zi_p8_argmax_x,
        Zi_p8_argmax_y,
        "o",
        color="navy",
        ms=5,
        label="4th order polynomial",
    )
    ax[4].plot(
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
        "o",
        color="black",
        ms=5,
        label="2D Gaussian fit (%2.2f, %2.2f)"
        % (G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y),
    )
    ax[4].get_xaxis().set_ticks([])
    ax[4].get_yaxis().set_ticks([])
    ax[4].set_title(
        "2D Gaussian CC"
        + "\n"
        + "RMSE: %2.3f, IQR: %2.3f (%d x %d)"
        % (G2D_rmse, G2D_iqr, corrcoef_G2D_img.shape[0], corrcoef_G2D_img.shape[1])
    )
    ax[4].legend()
    fig.suptitle("%s" % (fig_title), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_cc_patch(
    ref_img,
    sec_img,
    corrcoef_img,
    CC_argmax_x,
    CC_argmax_y,
    Zi_argmax_x,
    Zi_argmax_y,
    G2D_fit_fine_argmax_x,
    G2D_fit_fine_argmax_y,
    fig_title,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=1, ncols=3, figsize=(16, 8), dpi=300, layout="constrained"
    )
    im0 = ax[0].imshow(
        ref_img,
        vmin=np.nanpercentile(ref_img, 2),
        vmax=np.nanpercentile(ref_img, 98),
        cmap="gray",
    )
    ax[0].get_xaxis().set_ticks([])
    ax[0].get_yaxis().set_ticks([])
    ax[0].set_title("Reference patch")
    im1 = ax[1].imshow(
        sec_img,
        vmin=np.nanpercentile(ref_img, 2),
        vmax=np.nanpercentile(ref_img, 98),
        cmap="gray",
    )
    ax[1].get_xaxis().set_ticks([])
    ax[1].get_yaxis().set_ticks([])
    ax[1].set_title("Secondary patch")
    h = plt.colorbar(im1, ax=ax[0:2], orientation="horizontal", shrink=0.8)
    h.set_label("Landsat Grayscale", fontsize=14)
    # extent: floats (left, right, bottom, top)
    im2 = ax[2].imshow(
        corrcoef_img,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=0,
        vmax=1,
        cmap="magma",
    )
    h = plt.colorbar(im2, ax=ax[2], orientation="horizontal", shrink=0.8)
    h.set_label("Pearson Correlation Coefficient", fontsize=14)
    ax[2].plot(
        CC_argmax_x, CC_argmax_y, "k+", ms=5, label="max. value from orig.matrix"
    )
    ax[2].plot(
        Zi_argmax_x, Zi_argmax_y, "o", color="gray", ms=5, label="2nd order polynomial"
    )
    ax[2].plot(
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
        "o",
        color="black",
        ms=5,
        label="Gaussian2D",
    )
    ax[2].get_xaxis().set_ticks([])
    ax[2].get_yaxis().set_ticks([])
    ax[2].set_title("Pearson Correlation Coefficient")
    ax[2].legend()
    fig.suptitle("%s" % (fig_title), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


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
    Zi_argmax_x = sr_coordx_fine[Zi_argmax]
    Zi_argmax_y = sr_coordy_fine[Zi_argmax]
    return p2_rmse, p2_iqr, Zi_fine, Zi_argmax_x, Zi_argmax_y


def fit_poly4D(coords, corrcoef_ar, coords_fine, basis):
    # fitting second order polynomial
    A = np.vstack(basis).T
    Z, r, rank, s = np.linalg.lstsq(A, corrcoef_ar, rcond=None)
    Zi = np.sum(
        Z[:, None]
        * np.array(get_basis(coords[:, 0], coords[:, 1], max_order)).reshape(
            len(basis), coords.shape[0]
        ),
        axis=0,
    )
    dz_p4 = corrcoef_ar - Zi
    p4_rmse = np.float32(np.sqrt(np.mean(np.square(dz_p4))))
    p4_iqr = np.float32(np.percentile(dz_p4, 75) - np.percentile(dz_p4, 25))
    # create fine mesh for evaluating function
    Zi_fine = np.sum(
        Z[:, None]
        * np.array(get_basis(coords_fine[:, 0], coords_fine[:, 1], max_order)).reshape(
            len(basis), coords_fine.shape[0]
        ),
        axis=0,
    )
    Zi_argmax = np.argmax(Zi_fine)
    Zi_argmax_x = coords_fine[Zi_argmax, 0]
    Zi_argmax_y = coords_fine[Zi_argmax, 1]
    return (
        p4_rmse,
        p4_iqr,
        Zi_fine.reshape(
            (
                int(np.sqrt(sr_coordx_fine.shape[0])),
                int(np.sqrt(sr_coordy_fine.shape[0])),
            )
        ),
        Zi_argmax_x,
        Zi_argmax_y,
    )


def fit_poly2D(coords, corrcoef_ar, coords_fine):
    # fitting second order polynomial
    A = np.c_[
        np.ones(coords.shape[0]),
        coords[:, :2],
        np.prod(coords[:, :2], axis=1),
        coords[:, :2] ** 2,
    ]
    Z, _, _, _ = np.linalg.lstsq(A, corrcoef_ar, rcond=None)
    Zi = (
        Z[0]
        + Z[1] * coords[:, 0]
        + Z[2] * coords[:, 1]
        + Z[3] * np.prod(coords, axis=1)
        + Z[4] * coords[:, 0] ** 2
        + Z[5] * coords[:, 1] ** 2
    )
    dz_p2 = corrcoef_ar - Zi.reshape(corrcoef_ar.shape)
    p2_rmse = np.float32(np.sqrt(np.mean(np.square(dz_p2))))
    p2_iqr = np.float32(np.percentile(dz_p2, 75) - np.percentile(dz_p2, 25))
    # Zi_max = np.argmax(Zi)
    # idx0, = np.where( (coords[Zi_max,0] == coords_fine[:,0]) & (coords[Zi_max,1] == coords_fine[:,1]) )[0]
    # coords_fine[idx0-10:idx0+10,:]
    # create fine mesh for evaluating function
    Zi_fine = (
        Z[0]
        + Z[1] * coords_fine[:, 0]
        + Z[2] * coords_fine[:, 1]
        + Z[3] * np.prod(coords_fine, axis=1)
        + Z[4] * coords_fine[:, 0] ** 2
        + Z[5] * coords_fine[:, 1] ** 2
    )
    Zi_argmax = np.argmax(Zi_fine)
    Zi_argmax_x = coords_fine[Zi_argmax, 0]
    Zi_argmax_y = coords_fine[Zi_argmax, 1]
    return (
        p2_rmse,
        p2_iqr,
        Zi_fine.reshape(
            (
                int(np.sqrt(sr_coordx_fine.shape[0])),
                int(np.sqrt(sr_coordy_fine.shape[0])),
            )
        ),
        Zi_argmax_x,
        Zi_argmax_y,
    )


def fit_Gaussian2D(coords, corrcoef_ar, coords_fine, Zi_argmax_x, Zi_argmax_y):
    # fit 2D gaussian
    if Zi_argmax_x - Xmax < 10:
        Zi_argmax_x = Xmax / 2
    if Zi_argmax_y - Ymax < 10:
        Zi_argmax_y = Ymax / 2
    initial_guess = (1, Zi_argmax_x, Zi_argmax_y, 20, 20, 0, 0)
    param, _ = scipy.optimize.curve_fit(
        f=Gaussian2D, xdata=coords.T, ydata=corrcoef_ar, p0=initial_guess
    )
    G2D_fit = Gaussian2D(coords.T, *param).reshape((R * 2 + 1, R * 2 + 1))
    dz_G2D = corrcoef_ar - G2D_fit.reshape(corrcoef_ar.shape)
    G2D_rmse = np.float32(np.sqrt(np.mean(np.square(dz_G2D))))
    G2D_iqr = np.float32(np.percentile(dz_G2D, 75) - np.percentile(dz_G2D, 25))
    G2D_fit_fine = Gaussian2D(coords_fine.T, *param)
    G2D_fit_fine_argmax = np.argmax(G2D_fit_fine)
    G2D_fit_fine_argmax_x = coords_fine[G2D_fit_fine_argmax, 0]
    G2D_fit_fine_argmax_y = coords_fine[G2D_fit_fine_argmax, 1]
    return (
        G2D_rmse,
        G2D_iqr,
        G2D_fit_fine.reshape(
            (
                int(np.sqrt(sr_coordx_fine.shape[0])),
                int(np.sqrt(sr_coordy_fine.shape[0])),
            )
        ),
        G2D_fit_fine_argmax_x,
        G2D_fit_fine_argmax_y,
    )


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
    #
    max_order = 4
    fname1 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    fname2 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP/LC08_L1TP_231076_20230715_20230724_02_T1_B8.TIF"
    fname1_os05 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    fname2_os05 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05/LC08_L1TP_231076_20230715_20230724_02_T1_B8.TIF"
    # fname1 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    block_size = 31
    block_size_os05 = 121
    search_radius = 3
    search_radius_os05 = 15
    oversampling = 5
    matching_step = 1
    nr_random_pixels = 10
    pngdirname = (
        "/raid2-gpu2/bodo/LANDSAT/P231R076/CORR_os01_and_os05_bs121_sr15_ms01_png"
    )
    if not os.path.exists(pngdirname):
        os.mkdir(pngdirname)

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
    if Landsat_B8_1.shape != Landsat_B8_2.shape:
        raise ValueError("img1 and img2 must have the same shape")
    if Landsat_B8_1.ndim != 2:
        raise ValueError("Only 2D arrays supported")

    year_name1 = os.path.basename(fname1).split("_")[3]
    year_name2 = os.path.basename(fname2).split("_")[3]

    logging.info("Setting up variables for os01")
    half_block_size = block_size / 2
    R = int(search_radius)
    hbs = int(half_block_size)
    bs = 2 * hbs + 1
    H, W = Landsat_B8_1.shape
    # Pad so that every pixel center is valid:
    pad_mode = "reflect"
    img1p = np.pad(Landsat_B8_1, ((hbs, hbs), (hbs, hbs)), mode=pad_mode)
    img2p = np.pad(
        Landsat_B8_2, ((hbs + R, hbs + R), (hbs + R, hbs + R)), mode=pad_mode
    )
    # Patches centered at every original pixel
    ref_patches = sliding_window_view(img1p, (bs, bs))
    # All candidate patches in img2 (including extra R border)
    cand_patches = sliding_window_view(img2p, (bs, bs))
    # For each (y, x), collect candidate patches in a (2R+1)x(2R+1) window
    disp_view = sliding_window_view(
        cand_patches, window_shape=(2 * R + 1, 2 * R + 1), axis=(0, 1)
    )
    # creating coordinates for fitting. Make sure to flip Y-axes coordinates
    sr_coordx, sr_coordy = np.meshgrid(
        np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
        np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
    )
    sr_coordx = sr_coordx.ravel() - np.max(sr_coordx) / 2
    sr_coordy = np.flipud(sr_coordy.ravel()) - np.max(sr_coordy) / 2
    coords = np.c_[sr_coordx, sr_coordy]
    basis = get_basis(coords[:, 0], coords[:, 1], max_order)
    coord_upsampling_factor = 10
    # sr_coordx_fine, sr_coordy_fine = np.meshgrid(
    #     np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    #     np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
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

    pngfn_os01 = []
    random_i = np.random.randint(2000, Landsat_B8_1.shape[0] - 2000, nr_random_pixels)
    random_j = np.random.randint(2000, Landsat_B8_1.shape[1] - 2000, nr_random_pixels)
    NN_CC_x_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    NN_CC_x_argmax.fill(np.nan)
    NN_CC_y_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    NN_CC_y_argmax.fill(np.nan)
    p2_CC_x_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_x_argmax.fill(np.nan)
    p2_CC_y_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_y_argmax.fill(np.nan)
    p4_CC_x_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    p4_CC_x_argmax.fill(np.nan)
    p4_CC_y_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    p4_CC_y_argmax.fill(np.nan)
    G2D_CC_x_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    G2D_CC_x_argmax.fill(np.nan)
    G2D_CC_y_argmax = np.empty((nr_random_pixels), dtype=np.float32)
    G2D_CC_y_argmax.fill(np.nan)
    for i in tqdm.tqdm(range(nr_random_pixels), desc="Iterate through random pixels"):
        # calculate corr. coef. for every pixel in search radius:
        sec = (
            disp_view[random_i[i], random_j[i], :, :, :, :]
            .reshape(
                disp_view.shape[2] * disp_view.shape[3],
                disp_view.shape[4] * disp_view.shape[5],
            )
            .T
        )
        if np.any(np.count_nonzero(sec, axis=0) < sr_coordx.shape[0]):
            continue
        # using custom function to calculate pearson Corr. from 2D vs 1D array:
        corrcoef_ar = pearsonr_2D(
            ref_patches[random_i[i], random_j[i], :, :].ravel(), sec
        )
        corrcoef_ar2D = corrcoef_ar.reshape((R * 2 + 1), (R * 2 + 1))
        CC_argmax = np.argmax(corrcoef_ar)
        NN_CC_x_argmax[i] = coords[CC_argmax, 0]
        NN_CC_y_argmax[i] = coords[CC_argmax, 1]
        CC_argmax_x = coords[CC_argmax, 0]
        CC_argmax_y = coords[CC_argmax, 1]
        CC_argmax_idx_x, CC_argmax_idx_y = np.unravel_index(
            CC_argmax, corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5]).shape
        )
        Xmin = np.min(sr_coordx)
        Xmax = np.max(sr_coordx)
        Ymin = np.min(sr_coordy)
        Ymax = np.max(sr_coordy)

        p2_rmse, p2_iqr, p2_Zi, Zi_argmax_x, Zi_argmax_y = fit_poly2D(
            coords, corrcoef_ar, coords_fine
        )
        G2D_rmse, G2D_iqr, G2D_Zi, G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y = (
            fit_Gaussian2D(coords, corrcoef_ar, coords_fine, Zi_argmax_x, Zi_argmax_y)
        )
        p4_rmse, p4_iqr, p4_Zi, Zi_p4_argmax_x, Zi_p4_argmax_y = fit_poly4D(
            coords, corrcoef_ar, coords_fine, basis
        )
        p2_CC_x_argmax[i] = Zi_argmax_x
        p2_CC_y_argmax[i] = Zi_argmax_y
        p4_CC_x_argmax[i] = Zi_p4_argmax_x
        p4_CC_y_argmax[i] = Zi_p4_argmax_y
        G2D_CC_x_argmax[i] = G2D_fit_fine_argmax_x
        G2D_CC_y_argmax[i] = G2D_fit_fine_argmax_y
        ref_img = ref_patches[random_i[i], random_j[i], :, :]
        corrcoef_img = corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5])
        pngfn = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d_x%05d_y%05d_CC_comparison.png" % (
            year_name1,
            year_name2,
            1,
            block_size,
            R,
            matching_step,
            random_i[i],
            random_j[i],
        )
        pngfn = os.path.join(pngdirname, pngfn)
        pngfn_os01.append(pngfn)
        fig_title = "%s-%s: Cor. Coef. comparison (px=%d, py=%d, bs=%d, sr=%d)" % (
            year_name1,
            year_name2,
            random_i[i],
            random_j[i],
            ref_img.shape[0],
            R,
        )
        plot_cc_fits(
            ref_img,
            corrcoef_img,
            p2_Zi,
            p8_Zi,
            G2D_Zi,
            CC_argmax_x,
            CC_argmax_y,
            Zi_argmax_x,
            Zi_argmax_y,
            Zi_p8_argmax_x,
            Zi_p8_argmax_y,
            G2D_fit_fine_argmax_x,
            G2D_fit_fine_argmax_y,
            p2_rmse,
            p2_iqr,
            G2D_rmse,
            G2D_iqr,
            fig_title,
            pngfn,
        )

    logging.info("Loading os05 Landsat TIFs: %s and %s" % (fname1, fname2))
    start0 = time.time()
    Landsat_B8_1, Landsat_1_ds_gt, Landsat_1_ds_proj, epsg_code = load_Landsat_tif(
        fname1_os05
    )
    Landsat_B8_2, Landsat_2_ds_gt, Landsat_2_ds_proj, epsg_code = load_Landsat_tif(
        fname2_os05
    )
    end = time.time()
    length_s = end - start0
    logging.info(
        "Loading Landsat data took %d seconds or %2.2f minutes"
        % (length_s, length_s / 60)
    )
    if Landsat_B8_1.shape != Landsat_B8_2.shape:
        raise ValueError("img1 and img2 must have the same shape")
    if Landsat_B8_1.ndim != 2:
        raise ValueError("Only 2D arrays supported")

    logging.info("Setting up variables for os05")
    half_block_size = block_size_os05 / 2
    R = int(search_radius_os05)
    hbs = int(half_block_size)
    bs = 2 * hbs + 1
    H, W = Landsat_B8_1.shape
    # Pad so that every pixel center is valid:
    pad_mode = "reflect"
    img1p = np.pad(Landsat_B8_1, ((hbs, hbs), (hbs, hbs)), mode=pad_mode)
    img2p = np.pad(
        Landsat_B8_2, ((hbs + R, hbs + R), (hbs + R, hbs + R)), mode=pad_mode
    )
    # Patches centered at every original pixel
    ref_patches = sliding_window_view(img1p, (bs, bs))
    # All candidate patches in img2 (including extra R border)
    cand_patches = sliding_window_view(img2p, (bs, bs))
    # For each (y, x), collect candidate patches in a (2R+1)x(2R+1) window
    disp_view = sliding_window_view(
        cand_patches, window_shape=(2 * R + 1, 2 * R + 1), axis=(0, 1)
    )
    # creating coordinates for fitting. Make sure to flip Y-axes coordinates
    sr_coordx, sr_coordy = np.meshgrid(
        np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
        np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
    )
    sr_coordx = sr_coordx.ravel()
    sr_coordy = np.flipud(sr_coordy.ravel())
    coords = np.c_[sr_coordx, sr_coordy]
    basis = get_basis(coords[:, 0], coords[:, 1], max_order)
    coord_upsampling_factor = 10
    sr_coordx_fine, sr_coordy_fine = np.meshgrid(
        np.arange(
            0,
            np.max(coords[:, 0]) + Landsat_1_ds_gt[1] / coord_upsampling_factor,
            Landsat_1_ds_gt[1] / coord_upsampling_factor,
        ),
        np.arange(
            0,
            np.max(coords[:, 0]) + Landsat_1_ds_gt[1] / coord_upsampling_factor,
            Landsat_1_ds_gt[1] / coord_upsampling_factor,
        ),
    )
    # sr_coordx_fine, sr_coordy_fine = np.meshgrid(
    #     np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    #     np.arange(0, ((R * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    # )
    sr_coordx_fine = sr_coordx_fine.ravel()
    sr_coordy_fine = np.flipud(sr_coordy_fine.ravel())
    Xmin_fine = np.min(sr_coordx_fine)
    Xmax_fine = np.max(sr_coordx_fine)
    Ymin_fine = np.min(sr_coordy_fine)
    Ymax_fine = np.max(sr_coordy_fine)
    coords_fine = np.c_[sr_coordx_fine, sr_coordy_fine]

    # random_i = np.random.randint(1000, Landsat_B8_1.shape[0]-1000, nr_random_pixels)
    # random_j = np.random.randint(1000, Landsat_B8_1.shape[1]-1000, nr_random_pixels)
    convert_txt = []
    random_i_os05 = random_i * 5
    random_j_os05 = random_j * 5
    CC_x_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    CC_x_argmax_os05.fill(np.nan)
    CC_y_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    CC_y_argmax_os05.fill(np.nan)
    p2_CC_x_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_x_argmax_os05.fill(np.nan)
    p2_CC_y_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_y_argmax_os05.fill(np.nan)
    p2_CC_x_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_x_argmax_os05.fill(np.nan)
    p2_CC_y_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    p2_CC_y_argmax_os05.fill(np.nan)
    G2D_CC_x_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    G2D_CC_x_argmax_os05.fill(np.nan)
    G2D_CC_y_argmax_os05 = np.empty((nr_random_pixels), dtype=np.float32)
    G2D_CC_y_argmax_os05.fill(np.nan)
    for i in tqdm.tqdm(range(nr_random_pixels), desc="Iterate through random pixels"):
        # calculate corr. coef. for every pixel in search radius:
        sec = (
            disp_view[random_i_os05[i], random_j_os05[i], :, :, :, :]
            .reshape(
                disp_view.shape[2] * disp_view.shape[3],
                disp_view.shape[4] * disp_view.shape[5],
            )
            .T
        )
        if np.count_nonzero(np.max(sec, axis=1)) < sr_coordx.shape[0]:
            continue
        # using custom function to calculate pearson Corr. from 2D vs 1D array:
        corrcoef_ar = pearsonr_2D(
            ref_patches[random_i_os05[i], random_j_os05[i], :, :].ravel(), sec
        )
        corrcoef_ar2D = corrcoef_ar.reshape((R * 2 + 1), (R * 2 + 1))
        CC_argmax = np.argmax(corrcoef_ar)
        CC_x_argmax_os05[i] = coords[CC_argmax, 0]
        CC_y_argmax_os05[i] = coords[CC_argmax, 1]
        CC_argmax_idx_x, CC_argmax_idx_y = np.unravel_index(
            CC_argmax, corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5]).shape
        )
        Xmin = np.min(sr_coordx)
        Xmax = np.max(sr_coordx)
        Ymin = np.min(sr_coordy)
        Ymax = np.max(sr_coordy)

        p2_rmse, p2_iqr, p2_Zi, Zi_argmax_x, Zi_argmax_y = fit_poly2D(
            coords, corrcoef_ar, coords_fine
        )
        G2D_rmse, G2D_iqr, G2D_Zi, G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y = (
            fit_Gaussian2D(coords, corrcoef_ar, coords_fine, Zi_argmax_x, Zi_argmax_y)
        )
        p8_rmse, p8_iqr, p8_Zi, Zi_p8_argmax_x, Zi_p8_argmax_y = fit_poly8D(
            coords, corrcoef_ar, coords_fine, basis
        )
        p2_CC_x_argmax_os05[i] = Zi_argmax_x
        p2_CC_y_argmax_os05[i] = Zi_argmax_y
        p8_CC_x_argmax[i] = Zi_p8_argmax_x
        p8_CC_y_argmax[i] = Zi_p8_argmax_y
        G2D_CC_x_argmax_os05[i] = G2D_fit_fine_argmax_x
        G2D_CC_y_argmax_os05[i] = G2D_fit_fine_argmax_y

        ref_img = ref_patches[random_i_os05[i], random_j_os05[i], :, :]
        corrcoef_img = corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5])
        pngfn = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d_x%05d_y%05d_CC_comparison.png" % (
            year_name1,
            year_name2,
            oversampling,
            block_size_os05,
            R,
            matching_step,
            random_i_os05[i],
            random_j_os05[i],
        )
        pngfn = os.path.join(pngdirname, pngfn)
        pngfn_combined = (
            "%s_%s_os01_and_os%02d_bs%02d_sr%02d_ms%02d_x%05d_y%05d_CC_comparison.png"
            % (
                year_name1,
                year_name2,
                oversampling,
                block_size_os05,
                R,
                matching_step,
                random_i_os05[i],
                random_j_os05[i],
            )
        )
        pngfn_combined = os.path.join(pngdirname, pngfn_combined)
        fig_title = "%s-%s: Cor. Coef. comparison (px=%d, py=%d, bs=%d, sr=%d)" % (
            year_name1,
            year_name2,
            random_i_os05[i],
            random_j_os05[i],
            ref_img.shape[0],
            R,
        )
        plot_cc_fits(
            ref_img,
            corrcoef_img,
            p2_Zi,
            p8_Zi,
            G2D_Zi,
            CC_argmax_x,
            CC_argmax_y,
            Zi_argmax_x,
            Zi_argmax_y,
            Zi_p8_argmax_x,
            Zi_p8_argmax_y,
            G2D_fit_fine_argmax_x,
            G2D_fit_fine_argmax_y,
            p2_rmse,
            p2_iqr,
            G2D_rmse,
            G2D_iqr,
            fig_title,
            pngfn,
        )
        convert_txt.append(
            "convert -quality 100 -density 300 %s %s -fuzz 1%% -trim -bordercolor white -border 0x50 +repage -append %s"
            % (pngfn_os01[i], pngfn, pngfn_combined)
        )

    with open("convert_command.cmd", "w") as f:
        for line in convert_txt:
            f.write(f"{line}\n")
