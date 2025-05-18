import numpy as np
import numba as nb
from block_matching import block_matching_ncc, block_matching_masked_ncc
from numba import cuda
from math import sqrt
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


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


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj


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


def save_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value):
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


def save_all_geotiff():
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_u_epsg%s.tif" % (
        block_size,
        search_radius,
        epsg_code,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(geotiff_fn, u, int(epsg_code), geotransform=gt, nan_value=np.nan)
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_v_epsg%s.tif" % (
        block_size,
        search_radius,
        epsg_code,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(geotiff_fn, v, int(epsg_code), geotransform=gt, nan_value=np.nan)
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_blocksizes_epsg%s.tif" % (
        block_size,
        search_radius,
        epsg_code,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn, block_sizes, int(epsg_code), geotransform=gt, nan_value=np.nan
    )
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_correlation_epsg%s.tif" % (
        block_size,
        search_radius,
        epsg_code,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn, correlation, int(epsg_code), geotransform=gt, nan_value=np.nan
    )


if __name__ == "__main__":

    fname1 = sys.argv[1]
    fname2 = sys.argv[2]
    block_size = int(sys.argv[3])
    search_radius = int(sys.argv[4])

    fname1 = "LC08_L1TP_231077_20130820_20200913_02_T1_B8.TIF"
    fname2 = "LC09_L1TP_231077_20240420_20240420_02_T1_B8.TIF"
    block_size = 9
    search_radius = 4

    logging.info("Loading Landsat TIFs: %s and %s" % (fname1, fname2))
    Landsat_B8_1, Landsat_1_ds_gt, Landsat_1_ds_proj = load_Landsat_tif(fname1)
    Landsat_B8_2, Landsat_2_ds_gt, Landsat_2_ds_proj = load_Landsat_tif(fname2)

    logging.info(
        "Running block matching for %s and %s with block size: %02d and search radius %02d"
        % (fname1, fname2, block_size, search_radius)
    )
    p = Landsat_B8_1
    q = Landsat_B8_2
    year_name1 = os.path.basename(fname1).split("_")[3]
    year_name2 = os.path.basename(fname2).split("_")[3]
    if os.path.basename(fname1).find("os") == -1:
        # no oversampling
        oversampling = 1
    else:
        oversampling = os.path.basename(fname1).split("_")[-2].split(".")[0]
    fname = "%s_%s_os%02d_bs%02d_sr%02d" % (
        year_name1,
        year_name2,
        oversampling,
        block_size,
        search_radius,
    )
    dirname = "%s_%s_os%02d" % (year_name1, year_name2, oversampling)
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    start = time.time()
    u, v, block_sizes, correlation = block_matching_ncc(p, q, block_size, search_radius)
    end = time.time()
    length_s = end - start
    logging.info("Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

    logging.info("Extract geotiff information from %s" % (fname1))
    gt, proj, epsg_code, ys, xs = get_geotiff_info(fname1)
    save_all_geotiff()
