import numpy as np
import numba as nb
from block_matching import block_matching_ncc, block_matching_masked_ncc
from numba import cuda
from math import sqrt
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys

gdal.UseExceptions()

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
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
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
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_ms%02d_u.tif" % (
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn, u, int(epsg_code), geotransform=Landsat_1_ds_gt, nan_value=np.nan
    )
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_ms%02d_v.tif" % (
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn, v, int(epsg_code), geotransform=Landsat_1_ds_gt, nan_value=np.nan
    )
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_ms%02d_blocksizes.tif" % (
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn,
        block_sizes,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )
    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_ms%02d_correlation.tif" % (
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn,
        correlation,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
        nan_value=np.nan,
    )


if __name__ == "__main__":

    fname1 = sys.argv[1]
    fname2 = sys.argv[2]
    block_size = int(sys.argv[3])
    search_radius = int(sys.argv[4])
    oversampling = int(sys.argv[5])
    matching_step = int(sys.argv[6])
    cudadevice = int(sys.argv[7])

    # 20130928_20231002
    # fname1 = "CROP_os03/LC08_L1TP_232077_20130928_20200912_02_T1_B8.TIF"  # os03/LC08_L1TP_231077_20130820_20200913_02_T1_B8.TIF"
    # fname2 = "CROP_os03/LC09_L1TP_232077_20231002_20231002_02_T1_B8.TIF"  # s03/LC09_L1TP_231077_20240420_20240420_02_T1_B8.TIF"
    # block_size = 61
    # search_radius = 6
    # cudadevice = 0
    # oversampling = 3
    # matching_step = 6

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
    logging.info("Loading took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

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
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    # logging.info("Extract geotiff information from %s" % (fname1))
    # gt, proj, epsg_code, ys, xs = get_geotiff_info(fname1)

    if matching_step != 1:
        logging.info("Masking skip steps with matching step of %02d" % matching_step)
        # apply skip stepsize
        # find center point: matching_step = 3, one step in and then in 3 steps
        Landsat_B8_mask = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        Landsat_B8_mask[1::matching_step, 1::matching_step] = 0
        # make sure to mask out nan area surrounding Landsat image
        Landsat_B8_mask[np.isnan(Landsat_B8_1)] = 1
        nr_nan_pixels1 = len(np.where(Landsat_B8_mask == 1)[0])
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
        Landsat_B8_mask[~np.isnan(Landsat_B8_1)] = 0
        nr_nan_pixels1 = len(np.where(Landsat_B8_mask == 1)[0])
        logging.info(
            "Masked %s nan pixels (%2.1f %%)"
            % (
                f"{nr_nan_pixels1:,}",
                nr_nan_pixels1 / (Landsat_B8_1.shape[0] * Landsat_B8_1.shape[1]) * 100,
            )
        )

    nr_of_correlation_pixels = len(np.where(Landsat_B8_mask == 0)[0])
    logging.info(
        "Running correlation for %s pixels (%02.1f %%)"
        % (
            f"{nr_of_correlation_pixels:,}",
            nr_of_correlation_pixels
            / (Landsat_B8_mask.shape[0] * Landsat_B8_mask.shape[1])
            * 100,
        )
    )

    geotiff_fn = os.path.basename(dirname) + "_bs%02d_sr%02d_ms%02d_mask.tif" % (
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_mask_geotiff(
        geotiff_fn, Landsat_B8_mask, epsg_code, geotransform=Landsat_1_ds_gt
    )

    logging.info(
        "Running block matching for %s and %s with block size: %02d and search radius %02d and matching step %02d"
        % (fname1, fname2, block_size, search_radius, matching_step)
    )
    start = time.time()
    u, v, block_sizes, correlation = block_matching_masked_ncc(
        Landsat_B8_1, Landsat_B8_2, Landsat_B8_mask, block_size, search_radius
    )
    end = time.time()
    length_s = end - start
    logging.info("Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

    start = time.time()
    save_all_geotiff()
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
