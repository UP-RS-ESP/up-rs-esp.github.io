import numpy as np
import numba as nb
from block_matching import (
    block_matching_masked_ncc_uint_nonzero,
    block_matching_masked_ncc_uint_nonzero_fullc,
)
from numba import cuda
from math import sqrt
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, tqdm, glob
import cupy as cp
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

mempool = cp.get_default_memory_pool()
pinned_mempool = cp.get_default_pinned_memory_pool()
gdal.UseExceptions()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


@nb.njit(parallel=True)
def calc_direction_velocity(u, v):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    direction = np.empty((u.shape), dtype=np.float32)
    direction.fill(np.nan)
    magnitude = np.empty((u.shape), dtype=np.float32)
    magnitude.fill(np.nan)
    for i in nb.prange(u.shape[0]):
        for j in nb.prange(u.shape[1]):
            magnitude[i, j] = np.sqrt(v[i, j] ** 2 + u[i, j] ** 2)
            if magnitude[i, j] == 0:
                continue
            else:
                direction[i, j] = ArithmeticDegree_to_GeographicDegree(
                    np.rad2deg(np.arctan2(v[i, j], u[i, j]))
                )
    return direction, magnitude


def load_dem_aspect_slope_files(dem_fname):
    logging.info("Loading DEM file %s" % dem_fname)
    dem, dem_gt, dem_proj, dem_epsg = load_Landsat_f32_tif(dem_fname)
    # dem_slope, dem_aspect = np_slope_aspect(dem, dem_gt[1])
    # !gdaldem aspect COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    # !gdaldem slope COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_slope.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    #!gdaldem hillshade COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif COP15_DEM_NW_ARGENTINA_UTM20_P231R077_hs.tif -co COMPRESS=DEFLATE -co ZLEVEL=9
    dem_dir = os.path.dirname(dem_fname)
    dem_basename = os.path.basename(dem_fname).split(".")[0]
    aspect_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_aspect.tif"))
    aspect_fname = aspect_fname_lst[0]
    logging.info("Loading DEM-aspect file %s" % aspect_fname)
    dem_aspect, aspect_gt, aspect_proj, aspect_epsg = load_Landsat_f32_tif(aspect_fname)
    dem_aspect[dem_aspect < 0] = np.nan
    slope_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_slope.tif"))
    slope_fname = slope_fname_lst[0]
    logging.info("Loading DEM-slope file %s" % slope_fname)
    dem_slope, slope_gt, slope_proj, slope_epsg = load_Landsat_f32_tif(slope_fname)
    dem_slope[dem_slope < 0] = np.nan
    hs_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_hs.tif"))
    hs_fname = hs_fname_lst[0]
    logging.info("Loading DEM-hillshade file %s" % hs_fname)
    dem_hs, hs_gt, hs_proj, hs_epsg = load_Landsat_tif8bit(hs_fname)
    dem_hs = np.ma.masked_where(np.isnan(dem_slope), dem_hs)
    return dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs


def write_patch_correlation_npy(u, v, block_sizes, correlation, dirname, fname):
    fname_u = os.path.join(dirname, fname + "_u.npy")
    np.save(fname_u, u)
    fname_v = os.path.join(dirname, fname + "_v.npy")
    np.save(fname_v, v)
    fname_bs = os.path.join(dirname, fname + "_bs.npy")
    np.save(fname_bs, block_sizes)
    fname_c = os.path.join(dirname, fname + "_correlation.npy")
    np.save(fname_c, correlation)


# Verify that cuda is available
cuda_status = cuda.detect()
if not cuda_status:
    logging.info("No CUDA found. Stopping.")
    sys.exit(-1)


def load_Landsat_tif8bit(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray())
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def load_mask_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint8")
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, int(epsg)


def load_Landsat_f32_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


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


def save_float32_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=0):
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
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_stddev.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_float32_geotiff(
        geotiff_fn,
        stddev,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )


def plot_6panel_comparison(
    dem_hs,
    dem,
    cc_magnitude,
    cc_direction,
    Zi_magnitude,
    Zi_direction,
    uv_magnitude,
    uv_direction,
    p2_rmse,
    xrandom,
    yrandom,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 10), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(
        dem,
        cmap="gist_earth",
    )
    ax[0, 0].plot(yrandom, xrandom, "wx", ms=10)
    ax[0, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal", shrink=0.7)
    h.set_label("elevation", fontsize=12)
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    im1 = ax[0, 1].imshow(
        cc_magnitude,
        cmap="viridis",
        vmin=np.nanpercentile(
            cc_magnitude, 2
        ),  # np.nanpercentile(cc_magnitude-uv_magnitude,2),
        vmax=np.nanpercentile(
            cc_magnitude, 98
        ),  # np.nanpercentile(cc_magnitude-uv_magnitude, 98),
    )
    ax[0, 1].plot(yrandom, xrandom, "kx", ms=10)
    im1b = ax[0, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="horizontal", shrink=0.7)
    # h.set_label(r"$\Delta$ CC-max minus MaxC Displacement magnitude", fontsize=12)
    h.set_label("CC-max Displacement magnitude", fontsize=12)
    ax[0, 1].get_xaxis().set_ticks([])
    ax[0, 1].get_yaxis().set_ticks([])
    im1 = ax[0, 2].imshow(
        Zi_magnitude - uv_magnitude,
        cmap="Spectral",
        vmin=-30,
        vmax=30,
    )
    ax[0, 2].plot(yrandom, xrandom, "kx", ms=10)
    im1b = ax[0, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 2], orientation="horizontal", shrink=0.7)
    h.set_label(r"$\Delta$ Zi minus MaxC Displacement magnitude", fontsize=12)
    ax[0, 2].get_xaxis().set_ticks([])
    ax[0, 2].get_yaxis().set_ticks([])
    # im2 = ax[0, 2].imshow(
    #     cc_direction - uv_direction,
    #     cmap="hsv",
    #     vmin=-90,
    #     vmax=90,
    # )
    # im2b = ax[0, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    # h = plt.colorbar(im2, ax=ax[0, 2], orientation="horizontal", shrink=0.7)
    # h.set_label(r"$\Delta$ FullC minus MaxC Displacement direction", fontsize=12)
    # ax[0, 2].get_xaxis().set_ticks([])
    # ax[0, 2].get_yaxis().set_ticks([])
    # im3 = ax[1, 0].imshow(
    #     p2_rmse,
    #     cmap="Blues",
    # )
    # im3b = ax[1, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    # h = plt.colorbar(im3, ax=ax[1, 0], orientation="horizontal", shrink=0.7)
    # h.set_label("p2 - rmse", fontsize=12)
    # ax[1, 0].get_xaxis().set_ticks([])
    # ax[1, 0].get_yaxis().set_ticks([])
    im3 = ax[1, 0].imshow(
        uv_magnitude,
        cmap="viridis",
        vmin=np.nanpercentile(uv_magnitude, 2),
        vmax=np.nanpercentile(uv_magnitude, 98),
    )
    im3b = ax[1, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 0], orientation="horizontal", shrink=0.7)
    h.set_label("MaxC (uv) Displacement magnitude", fontsize=12)
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    im3 = ax[1, 1].imshow(
        Zi_magnitude,
        cmap="viridis",
        vmin=np.nanpercentile(Zi_magnitude, 2),
        vmax=np.nanpercentile(Zi_magnitude, 98),
    )
    im3b = ax[1, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 1], orientation="horizontal", shrink=0.7)
    h.set_label("Zi Displacement magnitude", fontsize=12)
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    im4 = ax[1, 2].imshow(
        Zi_fine_magnitude,
        cmap="viridis",
        vmin=np.nanpercentile(Zi_magnitude, 2),
        vmax=np.nanpercentile(Zi_magnitude, 98),
    )
    im3b = ax[1, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 2], orientation="horizontal", shrink=0.7)
    h.set_label("Zi fine Displacement magnitude", fontsize=12)
    ax[1, 2].get_xaxis().set_ticks([])
    ax[1, 2].get_yaxis().set_ticks([])
    # im3 = ax[1, 2].imshow(
    #     uv_direction,
    #     cmap="hsv",
    #     vmin=0,
    #     vmax=360,
    # )
    # im3b = ax[1, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    # h = plt.colorbar(im3, ax=ax[1, 2], orientation="horizontal", shrink=0.7)
    # h.set_label("MaxC Displacement direction", fontsize=12)
    # ax[1, 2].get_xaxis().set_ticks([])
    # ax[1, 2].get_yaxis().set_ticks([])
    fig.suptitle("%s" % (os.path.basename(pngfn)), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_6panel_variablesetup(
    coords_notflipped_x,
    coords_notflipped_y,
    coords_x,
    coords_y,
    coords_fine_x,
    coords_fine_y,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 10), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(
        coords_notflipped_x,
        cmap="viridis",
    )
    ax[0, 0].set_title("coords_notflipped_x")
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal", shrink=0.7)
    im1 = ax[1, 0].imshow(
        coords_notflipped_y,
        cmap="viridis",
    )
    ax[1, 0].set_title("coords_notflipped_y")
    h = plt.colorbar(im1, ax=ax[1, 0], orientation="horizontal", shrink=0.7)

    im0 = ax[0, 1].imshow(
        coords_x,
        cmap="viridis",
    )
    ax[0, 1].set_title("coords_x")
    h = plt.colorbar(im0, ax=ax[0, 1], orientation="horizontal", shrink=0.7)
    im1 = ax[1, 1].imshow(
        coords_y,
        cmap="viridis",
    )
    ax[1, 1].set_title("coords_y")
    h = plt.colorbar(im1, ax=ax[1, 1], orientation="horizontal", shrink=0.7)
    im0 = ax[0, 2].imshow(
        coords_fine_x,
        cmap="viridis",
    )
    ax[0, 2].set_title("coords_fine_x")
    h = plt.colorbar(im0, ax=ax[0, 2], orientation="horizontal", shrink=0.7)
    im1 = ax[1, 2].imshow(
        coords_fine_y,
        cmap="viridis",
    )
    ax[1, 2].set_title("coords_fine_y")
    h = plt.colorbar(im1, ax=ax[1, 2], orientation="horizontal", shrink=0.7)
    fig.suptitle("Coordinate Variable Setup", fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_6panel_overview(
    dem_hs,
    dem,
    cc_magnitude,
    cc_direction,
    p2_rmse,
    curvature_contour,
    curvature_profile,
    xrandom,
    yrandom,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 10), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(
        dem,
        cmap="gist_earth",
    )
    im0b = ax[0, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal", shrink=0.7)
    h.set_label("elevation", fontsize=12)
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    ax[0, 0].plot(yrandom, xrandom, "wx", ms=10)
    im1 = ax[0, 1].imshow(
        cc_magnitude,
        cmap="viridis",
        vmin=np.nanpercentile(cc_magnitude, 2),
        vmax=np.nanpercentile(cc_magnitude, 98),
    )
    im1b = ax[0, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="horizontal", shrink=0.7)
    h.set_label("Displacement magnitude", fontsize=12)
    ax[0, 1].get_xaxis().set_ticks([])
    ax[0, 1].get_yaxis().set_ticks([])
    ax[0, 1].plot(yrandom, xrandom, "wx", ms=10)
    im2 = ax[0, 2].imshow(
        cc_direction,
        cmap="hsv",
        vmin=0,
        vmax=360,
    )
    im2b = ax[0, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im2, ax=ax[0, 2], orientation="horizontal", shrink=0.7)
    h.set_label("Displacement direction", fontsize=12)
    ax[0, 2].get_xaxis().set_ticks([])
    ax[0, 2].get_yaxis().set_ticks([])
    im3 = ax[1, 0].imshow(
        p2_rmse,
        cmap="Blues",
    )
    im3b = ax[1, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 0], orientation="horizontal", shrink=0.7)
    h.set_label("p2 - rmse", fontsize=12)
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    im3 = ax[1, 1].imshow(
        curvature_contour,
        cmap="magma",
        vmin=np.nanpercentile(curvature_contour, 2),
        vmax=np.nanpercentile(curvature_contour, 98),
    )
    im3b = ax[1, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 1], orientation="horizontal", shrink=0.7)
    h.set_label("Curvature Contour", fontsize=12)
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    im3 = ax[1, 2].imshow(
        curvature_profile,
        cmap="magma",
        vmin=np.nanpercentile(curvature_profile, 2),
        vmax=np.nanpercentile(curvature_profile, 98),
    )
    im3b = ax[1, 2].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 2], orientation="horizontal", shrink=0.7)
    h.set_label("curvature Profile", fontsize=12)
    ax[1, 2].get_xaxis().set_ticks([])
    ax[1, 2].get_yaxis().set_ticks([])
    fig.suptitle("%s" % (os.path.basename(pngfn)), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_6panel_cc_matrix(
    u_coord,
    v_coord,
    CC_matrix,
    CC_maxx,
    CC_maxy,
    Zi,
    Zi_maxx,
    Zi_maxy,
    Zi_fine,
    Zi_fine_maxx,
    Zi_fine_maxy,
    p2_rmse,
    CC_matrix_log,
    CC_log_maxx,
    CC_log_maxy,
    Zi_log,
    Zi_log_maxx,
    Zi_log_maxy,
    Zi_log_fine,
    Zi_log_fine_maxx,
    Zi_log_fine_maxy,
    p2_log_rmse,
    fig_title,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 10), dpi=300, layout="constrained"
    )
    ax[0, 0].set_title("Original Correlation Matrix", fontsize=14)
    ax[0, 0].imshow(
        CC_matrix,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=0.5,
        vmax=1,
        cmap="magma",
    )
    ax[0, 0].plot(Zi_fine_maxx, Zi_fine_maxy, "k+", ms=5, label="fine Zi maxC")
    ax[0, 0].plot(Zi_maxx, Zi_maxy, "o", color="gray", ms=5, label="Zi maxC")
    ax[0, 0].plot(CC_maxx, CC_maxy, "o", color="black", ms=5, label="maxC")
    ax[0, 0].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
    ax[0, 0].legend()
    im1 = ax[0, 1].imshow(
        Zi,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=0.5,
        vmax=1,
        cmap="magma",
    )
    ax[0, 1].set_title(
        "Zi (%d x %d) with rmse: %2.3f" % (Zi.shape[0], Zi.shape[0], p2_rmse),
        fontsize=14,
    )
    ax[0, 1].plot(Zi_fine_maxx, Zi_fine_maxy, "k+", ms=5, label="fine Zi maxC")
    ax[0, 1].plot(Zi_maxx, Zi_maxy, "o", color="gray", ms=5, label="Zi maxC")
    ax[0, 1].plot(CC_maxx, CC_maxy, "o", color="black", ms=5, label="maxC")
    ax[0, 1].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
    h = plt.colorbar(im1, ax=ax[0, 0:2], orientation="horizontal", shrink=0.8)
    h.set_label("Correlation value", fontsize=14)
    sr_coordx_fine = np.arange(
        0,
        np.max(coords[:, 0])
        + np.max(sr_coordx)
        + Landsat_1_ds_gt[1] / coord_upsampling_factor,
        Landsat_1_ds_gt[1] / coord_upsampling_factor,
    )
    sr_coordy_fine = np.arange(
        0,
        np.max(coords[:, 0])
        + np.max(sr_coordx)
        + Landsat_1_ds_gt[1] / coord_upsampling_factor,
        Landsat_1_ds_gt[1] / coord_upsampling_factor,
    )
    sr_coordx_fine = sr_coordx_fine - np.max(sr_coordx_fine) / 2
    sr_coordy_fine = np.flipud(sr_coordy_fine) - np.max(sr_coordy_fine) / 2
    (x_start,) = np.argwhere(Zi_maxx - 5 < sr_coordx_fine)[0]
    (x_end,) = np.argwhere(Zi_maxx + 5 < sr_coordx_fine)[0]
    (y_end,) = np.argwhere(Zi_maxy - 5 < sr_coordy_fine)[-1]
    (y_start,) = np.argwhere(Zi_maxy + 5 < sr_coordy_fine)[-1]
    im2 = ax[0, 2].imshow(
        Zi_fine[x_start:x_end, y_start:y_end],
        extent=[
            sr_coordx_fine[x_start],
            sr_coordx_fine[x_end],
            sr_coordy_fine[y_start],
            sr_coordy_fine[y_end],
        ],
        vmin=np.percentile(Zi_fine[x_start:x_end, y_start:y_end], 2),
        vmax=np.percentile(Zi_fine[x_start:x_end, y_start:y_end], 98),
        cmap="plasma",
    )
    h = plt.colorbar(im2, ax=ax[0, 2], orientation="horizontal", shrink=0.8)
    h.set_label("Correlation value", fontsize=14)
    ax[0, 2].set_title(
        "Zi fine (%d x %d)" % (Zi_fine.shape[0], Zi_fine.shape[0]), fontsize=14
    )
    ax[0, 2].plot(Zi_fine_maxx, Zi_fine_maxy, "k+", ms=5, label="fine Zi maxC")
    ax[0, 2].plot(Zi_maxx, Zi_maxy, "o", color="gray", ms=5, label="Zi maxC")
    ax[0, 2].plot(CC_maxx, CC_maxy, "o", color="black", ms=5, label="maxC")
    ax[0, 2].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
    # Log CC_matrix
    ax[1, 0].set_title("Log Correlation Matrix", fontsize=14)
    ax[1, 0].imshow(
        CC_matrix_log,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=CC_matrix_log.min(),
        vmax=CC_matrix_log.max(),
        cmap="magma",
    )
    ax[1, 0].plot(
        Zi_log_fine_maxx, Zi_log_fine_maxy, "k+", ms=5, label="fine Zi_log maxC"
    )
    ax[1, 0].plot(
        Zi_log_maxx, Zi_log_maxy, "o", color="gray", ms=5, label="Zi_log maxC"
    )
    ax[1, 0].plot(CC_log_maxx, CC_log_maxy, "o", color="black", ms=5, label="lof maxC")
    ax[1, 0].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
    ax[1, 0].legend()
    im3 = ax[1, 1].imshow(
        Zi_log,
        interpolation="nearest",
        extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=CC_matrix_log.min(),
        vmax=CC_matrix_log.max(),
        cmap="magma",
    )
    h = plt.colorbar(im3, ax=ax[1, 0:2], orientation="horizontal", shrink=0.8)
    h.set_label("Log Correlation value", fontsize=14)
    ax[1, 1].set_title(
        "Zi_log (%d x %d) with rmse: %2.3f"
        % (Zi_log.shape[0], Zi_log.shape[0], p2_log_rmse),
        fontsize=14,
    )
    ax[1, 1].plot(
        Zi_log_fine_maxx, Zi_log_fine_maxy, "k+", ms=5, label="fine Zi_log maxC"
    )
    ax[1, 1].plot(
        Zi_log_maxx, Zi_log_maxy, "o", color="gray", ms=5, label="Zi_log maxC"
    )
    ax[1, 1].plot(CC_log_maxx, CC_log_maxy, "o", color="black", ms=5, label="log maxC")
    ax[1, 1].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
    (x_start,) = np.argwhere(Zi_log_maxx - 5 < sr_coordx_fine)[0]
    (x_end,) = np.argwhere(Zi_log_maxx + 5 < sr_coordx_fine)[0]
    (y_end,) = np.argwhere(Zi_log_maxy - 5 < sr_coordy_fine)[-1]
    (y_start,) = np.argwhere(Zi_log_maxy + 5 < sr_coordy_fine)[-1]
    im4 = ax[1, 2].imshow(
        Zi_log_fine[x_start:x_end, y_start:y_end],
        extent=[
            sr_coordx_fine[x_start],
            sr_coordx_fine[x_end],
            sr_coordy_fine[y_start],
            sr_coordy_fine[y_end],
        ],
        vmin=np.percentile(Zi_log_fine[x_start:x_end, y_start:y_end], 2),
        vmax=np.percentile(Zi_log_fine[x_start:x_end, y_start:y_end], 98),
        cmap="plasma",
    )
    h = plt.colorbar(im4, ax=ax[1, 2], orientation="horizontal", shrink=0.8)
    h.set_label("Log Correlation value", fontsize=14)
    ax[1, 2].set_title(
        "Zi_log fine (%d x %d)" % (Zi_log_fine.shape[0], Zi_log_fine.shape[0]),
        fontsize=14,
    )
    ax[1, 2].plot(
        Zi_log_fine_maxx, Zi_log_fine_maxy, "k+", ms=5, label="fine Zi_log maxC"
    )
    ax[1, 2].plot(
        Zi_log_maxx, Zi_log_maxy, "o", color="gray", ms=5, label="Zi_log maxC"
    )
    ax[1, 2].plot(CC_log_maxx, CC_log_maxy, "o", color="black", ms=5, label="log maxC")
    ax[1, 2].plot(u_coord, v_coord, "o", color="magenta", ms=5, label="uv")
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


def fit_poly2D_finecoords_GPU(coords, corrcoef_ar, coords_fine, nr_ar_splits=50):
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
    cc_gpu = cp.asarray(corrcoef_ar.reshape(-1), dtype=cp.float32)
    cc_max_idx = cp.asnumpy(cp.argmax(cc_gpu))
    Z, _, _, _ = cp.linalg.lstsq(A, cc_gpu, rcond=None)
    Zi = (
        Z[0]
        + Z[1] * coords_gpu[:, 0]
        + Z[2] * coords_gpu[:, 1]
        + Z[3] * cp.prod(coords_gpu, axis=1)
        + Z[4] * coords_gpu[:, 0] ** 2
        + Z[5] * coords_gpu[:, 1] ** 2
    )
    Zi_max_idx = cp.asnumpy(cp.argmax(Zi))
    dz_p2 = cc_gpu - Zi
    p2_rmse = cp.asnumpy(cp.sqrt(cp.mean(cp.square(dz_p2))))
    # p2_iqr = cp.asnumpy(cp.percentile(dz_p2, [25, 75], axis=0) - cp.percentile(dz_p2, 25, axis=0))
    dz_p2 = None
    A = None
    cc_gpu = None
    coords_gpu = None
    Zi_cpu = cp.asnumpy(Zi)
    Zi = None
    del A, cc_gpu, coords_gpu, Zi
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    #
    coords_fine_gpu = cp.asarray(coords_fine, dtype=cp.float32)
    Zi_fine = (
        Z[0]
        + Z[1] * coords_fine_gpu[:, 0]
        + Z[2] * coords_fine_gpu[:, 1]
        + Z[3] * cp.prod(coords_fine_gpu, axis=1)
        + Z[4] * coords_fine_gpu[:, 0] ** 2
        + Z[5] * coords_fine_gpu[:, 1] ** 2
    )
    Zi_fine_max_idx = cp.asnumpy(cp.argmax(Zi_fine))
    coords_fine_gpu = None
    Zi_argmax_gpu = None
    Zi_fine_cpu = cp.asnumpy(Zi_fine)
    del (
        coords_fine_gpu,
        Zi_argmax_gpu,
        Zi_fine,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    return cc_max_idx, Zi_max_idx, p2_rmse, Zi_cpu, Zi_fine_cpu, Zi_fine_max_idx


def fit_poly2D_finecoords_GPU_ar(coords, corrcoef_ar, coords_fine, nr_ar_splits=50):
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
    cc_gpu = cp.asarray(corrcoef_ar, dtype=cp.float32)
    cc_max_idx = cp.asnumpy(cp.argmax(cc_gpu, axis=1))
    Z, _, _, _ = cp.linalg.lstsq(A, cc_gpu.T, rcond=None)
    Zi = (
        Z[0, :]
        + Z[1, :] * coords_gpu[:, 0, None]
        + Z[2, :] * coords_gpu[:, 1, None]
        + Z[3, :] * cp.prod(coords_gpu[:, cp.newaxis], axis=2)
        + Z[4, :] * coords_gpu[:, 0, None] ** 2
        + Z[5, :] * coords_gpu[:, 1, None] ** 2
    )
    Zi_max_idx = cp.asnumpy(cp.argmax(Zi, axis=0))
    dz_p2 = cc_gpu.T - Zi
    p2_rmse = cp.asnumpy(cp.sqrt(cp.mean(cp.square(dz_p2), axis=0)))
    # p2_iqr = cp.asnumpy(cp.percentile(dz_p2, [25, 75], axis=0) - cp.percentile(dz_p2, 25, axis=0))
    # Curvature calculation
    fxx = Z[4, :]
    fyy = Z[5, :]
    fxy = Z[3, :]
    fx = Z[1, :]
    fy = Z[2, :]
    # mean curvature (arithmetic average)
    c_m = -((1 + (fy**2)) * fxx - 2 * fxy * fx * fy + (1 + (fx**2)) * fyy) / (
        2 * ((fx**2) + (fy**2) + 1) ** (3 / 2)
    )
    # tangential (normal to gradient) curvature
    c_t = -(
        (fxx * (fy**2) - 2 * fxy * fx * fy + fyy * (fx**2))
        / (((fx**2) + (fy**2)) * ((fx**2) + (fy**2) + 1) ** (1 / 2))
    )
    # difference (range of profile and tangential)
    c_d = c_m - c_t
    # profile (vertical or gradient direction) curvature
    c_p = c_m + c_d
    # contour (horizontal or contour direction) - plan curvature (i.e. contour curvature)
    c_c = -(
        (fxx * (fx**2) - 2 * fxy * fx * fy + fyy * (fx**2))
        / (((fx**2) + (fy**2)) ** (3 / 2))
    )
    c_simple = 2 * fxx + 2 * fyy
    curvatures = cp.asnumpy(cp.c_[c_simple, c_m, c_c, c_p, c_t])
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
    Zi_fine_argmax_gpu_x = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_fine_argmax_gpu_x.fill(cp.nan)
    Zi_fine_argmax_gpu_y = cp.empty(
        (nr_ar_splits, int(cp.ceil(Z.shape[1] / nr_ar_splits))), dtype=cp.float32
    )
    Zi_fine_argmax_gpu_y.fill(cp.nan)
    # for ii in tqdm.tqdm(range(nr_ar_splits), desc='Calculating peaks'):
    for ii in range(nr_ar_splits):
        Z_cp_tile = cp.array_split(Z, nr_ar_splits, axis=1)[ii]
        Zi_fine_fine = (
            Z_cp_tile[0, :]
            + Z_cp_tile[1, :] * coords_fine_gpu[:, 0, None]
            + Z_cp_tile[2, :] * coords_fine_gpu[:, 1, None]
            + Z_cp_tile[3, :] * cp.prod(coords_fine_gpu[:, np.newaxis], axis=2)
            + Z_cp_tile[4, :] * coords_fine_gpu[:, 0, None] ** 2
            + Z_cp_tile[5, :] * coords_fine_gpu[:, 1, None] ** 2
        )
        Zi_fine_argmax_gpu = cp.argmax(Zi_fine_fine, axis=0)
        Zi_fine_argmax_gpu_x[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[
            Zi_fine_argmax_gpu, 0
        ]
        Zi_fine_argmax_gpu_y[ii, 0 : Z_cp_tile.shape[1]] = coords_fine_gpu[
            Zi_fine_argmax_gpu, 1
        ]
    Zi_fine_argmax_gpu_x = cp.concatenate(Zi_fine_argmax_gpu_x)
    Zi_fine_argmax_gpu_x = Zi_fine_argmax_gpu_x[~cp.isnan(Zi_fine_argmax_gpu_x)]
    Zi_fine_argmax_x = cp.asnumpy(Zi_fine_argmax_gpu_x)
    Zi_fine_argmax_gpu_y = cp.concatenate(Zi_fine_argmax_gpu_y)
    Zi_fine_argmax_gpu_y = Zi_fine_argmax_gpu_y[~cp.isnan(Zi_fine_argmax_gpu_y)]
    Zi_fine_argmax_y = cp.asnumpy(Zi_fine_argmax_gpu_y)
    Zi_fine_argmax_gpu_x = None
    Zi_fine_argmax_gpu_y = None
    coords_fine_gpu = None
    Z_cp_tile = None
    Zi_fine = None
    Z = None
    Zi_fine_argmax_gpu = None
    del (
        Zi_fine_argmax_gpu_x,
        Zi_fine_argmax_gpu_y,
        coords_fine_gpu,
        Z_cp_tile,
        Zi_fine,
        Z,
        Zi_fine_argmax_gpu,
    )
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    return (
        cc_max_idx,
        Zi_max_idx,
        p2_rmse,
        Zi_fine_argmax_x,
        Zi_fine_argmax_y,
        curvatures,
    )


def fit_poly2D_GPU_ar(coords, corrcoef_ar):
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
    cc_gpu = cp.asarray(corrcoef_ar, dtype=cp.float32)
    cc_max_idx = cp.asnumpy(cp.argmax(cc_gpu, axis=1))
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
    # Curvature calculation
    fxx = Z[4, :]
    fyy = Z[5, :]
    fxy = Z[3, :]
    fx = Z[1, :]
    fy = Z[2, :]
    # mean curvature (arithmetic average)
    c_m = -((1 + (fy**2)) * fxx - 2 * fxy * fx * fy + (1 + (fx**2)) * fyy) / (
        2 * ((fx**2) + (fy**2) + 1) ** (3 / 2)
    )
    # tangential (normal to gradient) curvature
    c_t = -(
        (fxx * (fy**2) - 2 * fxy * fx * fy + fyy * (fx**2))
        / (((fx**2) + (fy**2)) * ((fx**2) + (fy**2) + 1) ** (1 / 2))
    )
    # difference (range of profile and tangential)
    c_d = c_m - c_t
    # profile (vertical or gradient direction) curvature
    c_p = c_m + c_d
    # contour (horizontal or contour direction) - plan curvature (i.e. contour curvature)
    c_c = -(
        (fxx * (fx**2) - 2 * fxy * fx * fy + fyy * (fx**2))
        / (((fx**2) + (fy**2)) ** (3 / 2))
    )
    c_simple = 2 * fxx + 2 * fyy
    curvatures = cp.asnumpy(cp.c_[c_simple, c_m, c_c, c_p, c_t])
    dz_p2 = None
    A = None
    cc_gpu = None
    coords_gpu = None
    Zi = None
    Z = None
    c_m, c_t, c_d, c_p, c_c, c_simple = None, None, None, None, None, None
    del A, cc_gpu, coords_gpu, Zi, Z
    mempool.free_all_blocks()
    pinned_mempool.free_all_blocks()
    #
    return cc_max_idx, p2_rmse, curvatures


if __name__ == "__main__":
    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching.py \
    #   /work/bookhage/Landsat/P231R078/corr_dates_sd1_cc20 \
    #   /work/bookhage/Landsat/P231R078/run_block_matching_231078_os05_bs121_sr08_ms05.bash \
    #   231078 121 8 5 5 2 \
    #   /work/bookhage/Landsat/P231R078/CORR_os05_bs121_sr08_ms05

    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching_mask.py \
    #   /work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF \
    #   /work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF \
    #   121 9 5 1 0 \
    #   /work/bookhage/Landsat/P231R076/CORR_os05_bs121_sr09_ms01 \
    #   /work/bookhage/Landsat/P231R076/251210_landslide_buffer_P231R076.tif

    fname1 = sys.argv[1]
    fname2 = sys.argv[2]
    block_size = int(sys.argv[3])
    search_radius = int(sys.argv[4])
    oversampling = int(sys.argv[5])
    matching_step = int(sys.argv[6])
    cudadevice = int(sys.argv[7])
    tifdirname = sys.argv[8]
    maskfname = sys.argv[9]
    nthreads_exp = 9
    Landsat_mask_exists = True

    # cd /work/bookhage/Landsat/P231R076/
    # conda activate numba
    # fname1 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    fname1 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05_clip/LC08_L1TP_231076_20130703_20200912_02_T1_B8.TIF"
    fname2 = "/raid2-gpu2/bodo/LANDSAT/P231R076/CROP_os05_clip/LC08_L1TP_231076_20240717_20240723_02_T1_B8.TIF"
    tifdirname = "/raid2-gpu2/bodo/LANDSAT/P231R076/CORR_os05_bs91_sr15_ms01"
    block_size = 91
    search_radius = 15
    cudadevice = 0
    oversampling = 5
    matching_step = 1
    satellite_resolution = 15
    # tifdirname ='/work/bookhage/Landsat/P231R076/CORR_os05_bs121_sr09_ms01'
    # maskfname='/work/bookhage/Landsat/P231R076/251210_landslide_buffer_P231R076.tif'
    maskfname = "/raid2-gpu2/bodo/LANDSAT/P231R076/251210_landslide_buffer_P231R076_os05_clip.tif"
    # gdalwarp -tr 3 3 -r nearest -multi -co BIGTIFF=YES -co COMPRESS=DEFLATE -co ZLEVEL=7 251210_landslide_buffer_P231R076.tif landslide_buffer_P231R076_os5.tif
    #
    # Create smaller clip for P231R076:
    # gdal_translate -projwin 290882 -2562781 303264 -2575637 -a_nodata 0.0 -of GTiff \
    # -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
    # CROP_os05/LC08_L1TP_231076_20130703_20200912_02_T1_B8.TIF \
    # CROP_os05_clip/LC08_L1TP_231076_20130703_20200912_02_T1_B8.TIF
    #
    # gdal_translate -projwin 290882 -2562781 303264 -2575637 -a_nodata 0.0 -of GTiff \
    # -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
    # CROP_os05/LC08_L1TP_231076_20240717_20240723_02_T1_B8.TIF \
    # CROP_os05_clip/LC08_L1TP_231076_20240717_20240723_02_T1_B8.TIF
    #
    # gdal_translate -projwin 290882 -2562781 303264 -2575637 -a_nodata 0.0 -of GTiff \
    # -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
    # COP15_DEM_ARGENTINA_UTM20_P231R076_os05.tif \
    # COP15_DEM_ARGENTINA_UTM20_P231R076_os05_clip.tif
    #
    # gdal_translate -projwin 290882 -2562781 303264 -2575637 -a_nodata 0.0 -of GTiff \
    # -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
    # 251210_landslide_buffer_P231R076_os05.tif \
    # 251210_landslide_buffer_P231R076_os05_clip.tif
    #
    #
    dem_fname = "/raid2-gpu2/bodo/LANDSAT/P231R076/COP15_DEM_ARGENTINA_UTM20_P231R076_os05_clip.tif"
    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )

    cuda.select_device(cudadevice)
    logging.info("Using CUDA Device %d" % cudadevice)
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

    logging.info("Setting Up Coordinates")
    sr_coordx, sr_coordy = np.meshgrid(
        np.arange(
            0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]
        ),
        np.arange(
            0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]
        ),
    )
    sr_coordx = sr_coordx.ravel() - np.max(sr_coordx) / 2
    sr_coordy = sr_coordy.ravel() - np.max(sr_coordy) / 2
    coords_notflipped = np.c_[sr_coordx, sr_coordy]
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
    # sr_coordy = sr_coordy.ravel() - np.max(sr_coordy) / 2
    coords = np.c_[sr_coordx, sr_coordy]
    Xmin = np.min(sr_coordx)
    Xmax = np.max(sr_coordx)
    Ymin = np.min(sr_coordy)
    Ymax = np.max(sr_coordy)
    coord_upsampling_factor = 5
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

    pngdirname = tifdirname + "_fullC_png"
    if not os.path.exists(pngdirname):
        os.mkdir(pngdirname)
    dirname = "%s_%s_os%02d" % (year_name1, year_name2, oversampling)
    geotiff_fn_c = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_cfull.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )

    if os.path.exists(geotiff_fn_c):
        logging.info("Files exists: %s" % (geotiff_fn_c))
        logging.info("exit")
        exit()

    if not os.path.exists(tifdirname):
        os.mkdir(tifdirname)

    if matching_step == 1:
        logging.info("Using mask for nan areas")
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

    logging.info(
        "Running maxC block matching for %s and %s with block size: %02d and search radius %02d and matching step %02d and nthreads_exp %02d"
        % (fname1, fname2, block_size, search_radius, matching_step, nthreads_exp)
    )
    start = time.time()
    # block_matching_masked_ncc_uint_nonzero(p, q, mask, block_size, search_radius, nthreads_exp=10)
    u, v, correlation, stddev = block_matching_masked_ncc_uint_nonzero(
        Landsat_B8_1,
        Landsat_B8_2,
        Landsat_B8_mask,
        block_size,
        search_radius,
        nthreads_exp=nthreads_exp,
    )
    end = time.time()
    length_s = end - start
    logging.info("Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

    u = u.astype(np.float32)
    u[u == -128] = np.nan
    u = u * satellite_resolution / oversampling
    v = v.astype(np.float32)
    v[v == -128] = np.nan
    v = v * satellite_resolution / oversampling

    logging.info(
        "Running fullC block matching for %s and %s with block size: %02d and search radius %02d and matching step %02d and nthreads_exp %02d"
        % (fname1, fname2, block_size, search_radius, matching_step, nthreads_exp)
    )
    start = time.time()
    c, ir, jr = block_matching_masked_ncc_uint_nonzero_fullc(
        Landsat_B8_1,
        Landsat_B8_2,
        Landsat_B8_mask,
        block_size,
        search_radius,
        nthreads_exp=nthreads_exp,
    )
    end = time.time()
    length_s = end - start
    logging.info(
        "FullC tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    )
    # maxc = np.max(c, axis=(1, 2))
    #    corrcoef_ar = c.reshape(-1, ((search_radius * 2) + 1) ** 2)

    logging.info("Calculating polynomial fit for %s pixels" % f"{c.shape[0]:,}")
    # Have to split c into smaller chunks if larger than 1e5 on 32GB GPU
    start = time.time()
    nre_gpu = 1e6
    nr_of_ar_splits = int(np.ceil(c.shape[0] / nre_gpu))
    corrcoef_ars = np.array_split(
        c.reshape(-1, ((search_radius * 2) + 1) ** 2), nr_of_ar_splits
    )
    cc_max_idx_ar = []
    p2_rmse_ar = []
    curvatures_ar = []
    Zi_fine_x_ar = []
    Zi_fine_y_ar = []
    Zi_x_ar = []
    Zi_y_ar = []
    for i in tqdm.tqdm(range(nr_of_ar_splits)):
        corrcoef_ar = corrcoef_ars[i]
        (
            cc_max_idx,
            Zi_max_idx,
            p2_rmse,
            Zi_fine_argmax_x,
            Zi_fine_argmax_y,
            curvatures,
        ) = fit_poly2D_finecoords_GPU_ar(
            coords, corrcoef_ar, coords_fine, nr_ar_splits=50
        )
        # cc_max_idx, p2_rmse, Zi_p2_x, Zi_p2_y = fit_poly2D_finecoords_GPU_ar(
        #     coords, corrcoef_ar, coords_fine
        # )
        cc_max_idx_ar.append(cc_max_idx)
        p2_rmse_ar.append(p2_rmse)
        Zi_x_ar.append(coords_notflipped[Zi_max_idx, 0])
        Zi_y_ar.append(coords_notflipped[Zi_max_idx, 1])
        Zi_fine_x_ar.append(Zi_fine_argmax_x)
        Zi_fine_y_ar.append(Zi_fine_argmax_y)
        curvatures_ar.append(curvatures)
    p2_rmse, cc_max_idx, curvatures, Zi_fine_argmax_x, Zi_fine_argmax_y = (
        None,
        None,
        None,
        None,
        None,
    )
    p2_rmse_ar = np.concatenate(p2_rmse_ar)
    cc_max_idx_ar = np.concatenate(cc_max_idx_ar)
    Zi_fine_x_ar = np.concatenate(Zi_fine_x_ar)
    Zi_fine_y_ar = np.concatenate(Zi_fine_y_ar)
    Zi_x_ar = np.concatenate(Zi_x_ar)
    Zi_y_ar = np.concatenate(Zi_y_ar)
    curvatures_ar = np.concatenate(curvatures_ar)
    # maxx, maxy = np.unravel_index(cc_max_idx_ar, (c.shape[1], c.shape[2]))
    end = time.time()
    length_s = end - start
    logging.info(
        "Polynomial function of 2nd order: Calculation took %d seconds or %2.2f minutes"
        % (length_s, length_s / 60)
    )

    logging.info("Sort back into original array")
    cc_mask = np.zeros(Landsat_B8_1.shape, dtype=np.bool_)
    p2_rmse = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    p2_rmse.fill(np.nan)
    p2_rmse = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    p2_rmse.fill(np.nan)
    cc_maxx = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    cc_maxx.fill(np.nan)
    cc_maxy = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    cc_maxy.fill(np.nan)
    curvature_contour = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    curvature_contour.fill(np.nan)
    curvature_profile = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    curvature_profile.fill(np.nan)
    Zi_x = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_x.fill(np.nan)
    Zi_y = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_y.fill(np.nan)
    Zi_fine_x = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_fine_x.fill(np.nan)
    Zi_fine_y = np.empty(Landsat_B8_1.shape, dtype=np.float32)
    Zi_fine_y.fill(np.nan)
    cc_mask[ir, jr] = 1
    p2_rmse[ir, jr] = p2_rmse_ar
    cc_maxx[ir, jr] = coords_notflipped[cc_max_idx_ar, 0]
    cc_maxy[ir, jr] = coords_notflipped[cc_max_idx_ar, 1]
    Zi_x[ir, jr] = Zi_x_ar
    Zi_y[ir, jr] = Zi_y_ar
    Zi_fine_x[ir, jr] = Zi_fine_x_ar
    Zi_fine_y[ir, jr] = Zi_fine_y_ar
    curvature_contour[ir, jr] = curvatures_ar[:, 2]
    curvature_profile[ir, jr] = curvatures_ar[:, 3]

    logging.info("Calculate magnitude")
    cc_direction, cc_magnitude = calc_direction_velocity(cc_maxx, cc_maxy)
    Zi_direction, Zi_magnitude = calc_direction_velocity(Zi_x, Zi_y)
    Zi_fine_direction, Zi_fine_magnitude = calc_direction_velocity(Zi_fine_x, Zi_fine_y)
    uv_direction, uv_magnitude = calc_direction_velocity(u, v)

    # plot scatter
    fig, ax = plt.subplots(
        nrows=3,
        ncols=2,
        sharex=True,
        sharey=True,
        figsize=(16, 16),
        dpi=300,
        layout="constrained",
    )
    ax[0, 0].plot(cc_magnitude.ravel(), Zi_magnitude.ravel(), "o", ms=1)
    ax[0, 0].plot([0, 80], [0, 80], "k-")
    ax[0, 0].set_ylabel("Zi velocity magnitude (m)", fontsize=14)
    ax[0, 0].set_xlabel("CC-max velocity magnitude (m)", fontsize=14)
    ax[0, 0].grid()
    ax[0, 0].set_xlim([0, 80])
    ax[0, 0].set_ylim([0, 80])
    ax[0, 1].plot(cc_magnitude.ravel(), Zi_fine_magnitude.ravel(), "o", ms=1)
    ax[0, 1].plot([0, 80], [0, 80], "k-")
    ax[0, 1].set_ylabel("Zi fine velocity magnitude (m)", fontsize=14)
    ax[0, 1].set_xlabel("CC-max velocity magnitude (m)", fontsize=14)
    ax[0, 1].grid()
    ax[0, 1].set_xlim([0, 80])
    ax[0, 1].set_ylim([0, 80])
    ax[1, 0].plot(uv_magnitude.ravel(), cc_magnitude.ravel(), "o", ms=1)
    ax[1, 0].plot([0, 80], [0, 80], "k-")
    ax[1, 0].set_ylabel("CC-max velocity magnitude (m)", fontsize=14)
    ax[1, 0].set_xlabel("uv velocity magnitude (m)", fontsize=14)
    ax[1, 0].grid()
    ax[1, 0].set_xlim([0, 80])
    ax[1, 0].set_ylim([0, 80])
    ax[1, 1].plot(uv_magnitude.ravel(), Zi_magnitude.ravel(), "o", ms=1)
    ax[1, 1].plot([0, 80], [0, 80], "k-")
    ax[1, 1].set_ylabel("Zi velocity magnitude (m)", fontsize=14)
    ax[1, 1].set_xlabel("uv velocity magnitude (m)", fontsize=14)
    ax[1, 1].grid()
    ax[1, 1].set_xlim([0, 80])
    ax[1, 1].set_ylim([0, 80])
    ax[2, 0].plot(uv_magnitude.ravel(), cc_magnitude.ravel(), "o", ms=1)
    ax[2, 0].set_ylabel("CC-max velocity magnitude (m)", fontsize=14)
    ax[2, 0].set_xlabel("uv velocity magnitude (m)", fontsize=14)
    ax[2, 0].grid()
    ax[2, 0].set_xlim([0, 80])
    ax[2, 0].set_ylim([0, 80])
    ax[2, 1].plot(Zi_magnitude.ravel(), Zi_fine_magnitude.ravel(), "o", ms=1)
    ax[2, 1].plot([0, 80], [0, 80], "k-")
    ax[2, 1].set_ylabel("Zi fine velocity magnitude (m)", fontsize=14)
    ax[2, 1].set_xlabel("Zi velocity magnitude (m)", fontsize=14)
    ax[2, 1].grid()
    ax[2, 1].set_xlim([0, 80])
    ax[2, 1].set_ylim([0, 80])
    fig.savefig(
        "/raid2-gpu2/bodo/LANDSAT/P231R076/CORR_os05_bs91_sr15_ms01_fullC_png/20130703_20240717_os05_bs91_sr15_ms01_CC_velocity_comparison.png",
        dpi=300,
    )
    plt.close()

    logging.info("Extracting random locations")
    Landsat_B8_mask_values = np.ones(Landsat_B8_mask.shape, dtype=np.bool_)
    Landsat_B8_mask_values[ir, jr] = False
    xy_values = np.nonzero(
        ~Landsat_B8_mask_values
    )  # select only pixels that are not masked outRaster
    # random choice with select random locations weighted by velocity: Faster pixels are more likely to get chosen
    ridx = np.random.choice(
        range(len(xy_values[0])),
        size=10,
        replace=False,
        p=cc_magnitude[xy_values[0], xy_values[1]]
        / np.sum(cc_magnitude[xy_values[0], xy_values[1]]),
    )
    xrandom = xy_values[0][ridx]
    yrandom = xy_values[1][ridx]
    logging.info("Plot overview and comparison with random locations")
    pngfn = os.path.join(pngdirname, fname + "_variable_setup.png")
    plot_6panel_variablesetup(
        coords_notflipped[:, 0].reshape(
            ((search_radius * 2) + 1, (search_radius * 2) + 1)
        ),
        coords_notflipped[:, 1].reshape(
            ((search_radius * 2) + 1, (search_radius * 2) + 1)
        ),
        coords[:, 0].reshape(((search_radius * 2) + 1, (search_radius * 2) + 1)),
        coords[:, 1].reshape(((search_radius * 2) + 1, (search_radius * 2) + 1)),
        coords_fine[:, 0].reshape(
            (
                int(np.sqrt(sr_coordx_fine.shape[0])),
                int(np.sqrt(sr_coordx_fine.shape[0])),
            )
        ),
        coords_fine[:, 1].reshape(
            (
                int(np.sqrt(sr_coordx_fine.shape[0])),
                int(np.sqrt(sr_coordx_fine.shape[0])),
            )
        ),
        pngfn,
    )
    pngfn = os.path.join(pngdirname, fname + "_overview1.png")
    plot_6panel_overview(
        dem_hs,
        dem,
        Zi_magnitude,
        Zi_direction,
        p2_rmse,
        curvature_contour,
        curvature_profile,
        xrandom,
        yrandom,
        pngfn,
    )
    pngfn = os.path.join(pngdirname, fname + "_comparison_uv.png")
    plot_6panel_comparison(
        dem_hs,
        dem,
        cc_magnitude,
        cc_direction,
        Zi_magnitude,
        Zi_direction,
        uv_magnitude,
        uv_direction,
        p2_rmse,
        xrandom,
        yrandom,
        pngfn,
    )

    logging.info("Plotting random locations")
    for i in tqdm.tqdm(range(len(ridx))):
        xidx = xy_values[0][ridx[i]]
        yidx = xy_values[1][ridx[i]]
        u_coord = u[xidx, yidx]
        v_coord = v[xidx, yidx]
        CC_matrix = c[ridx[i], :, :].astype(np.float32) / 127
        cc_max_idx, Zi_max_idx, p2_rmse, Zi, Zi_fine, Zi_fine_max_idx = (
            fit_poly2D_finecoords_GPU(coords, CC_matrix, coords_fine)
        )
        CC_maxx = coords[cc_max_idx, 0]
        CC_maxy = coords[cc_max_idx, 1]
        Zi_maxx = coords[Zi_max_idx, 0]
        Zi_maxy = coords[Zi_max_idx, 1]
        Zi_fine_maxx = coords_fine[Zi_fine_max_idx, 0]
        Zi_fine_maxy = coords_fine[Zi_fine_max_idx, 1]
        Zi = Zi.reshape((c.shape[1], c.shape[2]))
        Zi_fine = Zi_fine.reshape(
            (int(np.sqrt(coords_fine.shape[0])), int(np.sqrt(coords_fine.shape[0])))
        )

        CC_matrix_log = np.log(CC_matrix + np.min(CC_matrix))
        CC_matrix_log -= np.min(CC_matrix_log)
        (
            cc_log_max_idx,
            Zi_log_max_idx,
            p2_log_rmse,
            Zi_log,
            Zi_log_fine,
            Zi_log_fine_max_idx,
        ) = fit_poly2D_finecoords_GPU(coords, CC_matrix_log, coords_fine)
        CC_log_maxx = coords[cc_log_max_idx, 0]
        CC_log_maxy = coords[cc_log_max_idx, 1]
        Zi_log_maxx = coords[Zi_log_max_idx, 0]
        Zi_log_maxy = coords[Zi_log_max_idx, 1]
        Zi_log_fine_maxx = coords_fine[Zi_log_fine_max_idx, 0]
        Zi_log_fine_maxy = coords_fine[Zi_log_fine_max_idx, 1]
        Zi_log = Zi_log.reshape((c.shape[1], c.shape[2]))
        Zi_log_fine = Zi_log_fine.reshape(
            (int(np.sqrt(coords_fine.shape[0])), int(np.sqrt(coords_fine.shape[0])))
        )

        pngfn = os.path.join(pngdirname, fname + "_CC_matrix_%06d.png" % ridx[i])
        fig_title = "Zi v=%2.2f m, CCmax v=%2.2f (x: %d, y: %d) at %06d" % (
            cc_magnitude[xy_values[0][ridx[i]], xy_values[1][ridx[i]]],
            uv_magnitude[xy_values[0][ridx[i]], xy_values[1][ridx[i]]],
            xidx,
            yidx,
            ridx[i],
        )
        print(fig_title)
        plot_6panel_cc_matrix(
            u_coord,
            v_coord,
            CC_matrix,
            CC_maxx,
            CC_maxy,
            Zi,
            Zi_maxx,
            Zi_maxy,
            Zi_fine,
            Zi_fine_maxx,
            Zi_fine_maxy,
            p2_rmse,
            CC_matrix_log,
            CC_log_maxx,
            CC_log_maxy,
            Zi_log,
            Zi_log_maxx,
            Zi_log_maxy,
            Zi_log_fine,
            Zi_log_fine_maxx,
            Zi_log_fine_maxy,
            p2_log_rmse,
            fig_title,
            pngfn,
        )

    start = time.time()
    save_all_geotiff(tifdirname)
    end = time.time()
    length_s = end - start
    logging.info(
        "Writing all tiles took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    )
    end = time.time()

    length_s = end - start0
    logging.info(
        "All steps combined took %d seconds or %2.2f minutes or %2.2f hours "
        % (length_s, length_s / 60, length_s / (60 * 60))
    )
