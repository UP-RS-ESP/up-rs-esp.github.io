from datetime import date
import numpy as np
import numba as nb
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib
import scipy.ndimage
import scipy.linalg

matplotlib.use("Agg")
import matplotlib.pyplot as plt

gdal.UseExceptions()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def load_offset_tif(fname):
    offset_ds = gdal.Open(fname)
    offset_ds_gt = offset_ds.GetGeoTransform()
    offset_ds_proj = offset_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=offset_ds_proj).GetAttrValue("AUTHORITY", 1))
    offset = np.array(offset_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    offset_ds = None
    return offset, offset_ds_gt, offset_ds_proj, epsg


def load_blockmatching_tif(fname, matchingstep=1):
    blockmatching_ds = gdal.Open(fname)
    blockmatching_ds_gt = blockmatching_ds.GetGeoTransform()
    blockmatching_ds_proj = blockmatching_ds.GetProjection()
    epsg = int(
        osr.SpatialReference(wkt=blockmatching_ds_proj).GetAttrValue("AUTHORITY", 1)
    )
    blockmatching_B1 = np.array(blockmatching_ds.GetRasterBand(1).ReadAsArray()).astype(
        np.float32
    )
    blockmatching_B1[blockmatching_B1 == -128] = np.nan
    blockmatching_ds = None
    if matchingstep == 1:
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 3:
        blockmatching_B1 = blockmatching_B1[1::matchingstep, 1::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 5:
        blockmatching_B1 = blockmatching_B1[2::matchingstep, 2::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 7:
        blockmatching_B1 = blockmatching_B1[3::matchingstep, 3::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg


def load_blockmatching_correlation_tif(fname, matchingstep=1):
    blockmatching_ds = gdal.Open(fname)
    blockmatching_ds_gt = blockmatching_ds.GetGeoTransform()
    blockmatching_ds_proj = blockmatching_ds.GetProjection()
    epsg = int(
        osr.SpatialReference(wkt=blockmatching_ds_proj).GetAttrValue("AUTHORITY", 1)
    )
    blockmatching_B1 = np.array(blockmatching_ds.GetRasterBand(1).ReadAsArray()).astype(
        np.float32
    )
    blockmatching_B1[blockmatching_B1 == 0] = np.nan
    blockmatching_B1 = blockmatching_B1 / 255.0
    blockmatching_ds = None
    if matchingstep == 1:
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 3:
        blockmatching_B1 = blockmatching_B1[1::matchingstep, 1::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 5:
        blockmatching_B1 = blockmatching_B1[2::matchingstep, 2::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg
    elif matchingstep == 7:
        blockmatching_B1 = blockmatching_B1[3::matchingstep, 3::matchingstep]
        return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg


def load_Landsat_tif8bit(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray())
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def load_correlation_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def get_geotiff_info(geotiff_fn):
    """
    Get Geotiff information from fn.
    """
    ds = gdal.Open(geotiff_fn)
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=proj).GetAttrValue("AUTHORITY", 1))
    data = ds.ReadAsArray()
    ys, xs = data.shape
    ds = None
    return gt, proj, epsg, ys, xs


def save_geotiff_8bit(geotiff_fn, array, epsg_code, geotransform, nan_value=255):
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
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=1"],
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


def load_mask(filename, mask_size):
    date1 = os.path.basename(filename).split("_")[0]
    date2 = os.path.basename(filename).split("_")[1]
    fname = os.path.join(
        "/".join(os.path.dirname(filename).split("/")[:-1]),
        "MASKS",
        "%s_%s_NDSI_NDVI_CLOUD_SHADOW_mask.tif" % (date1, date2),
    )
    if os.path.exists(fname):
        mask_ds = gdal.Open(fname)
        mask_ar = np.array(mask_ds.GetRasterBand(1).ReadAsArray()).astype(np.bool_)
    else:
        logging.info("Mask %s does not exist. Using no mask." % (fname))
        mask_ar = np.empty(mask_size, dtype=np.bool_)
        mask_ar.fill(False)
    return mask_ar


def get_deltaT_from_filename(filename):
    date1 = pd.to_datetime(os.path.basename(filename).split("_")[0])
    date2 = pd.to_datetime(os.path.basename(filename).split("_")[1])
    difference_in_years = relativedelta(date2, date1).years
    difference_in_days = relativedelta(date2, date1).days / 365.25
    difference_in_years += difference_in_days
    deltaT_y = difference_in_years
    return deltaT_y


def get_deltaT_from_filenames(v_files):
    deltaT_y = np.empty(len(v_files), dtype=np.float32)
    deltaT_y.fill(np.nan)
    for i in range(len(v_files)):
        date1 = pd.to_datetime(os.path.basename(v_files[i]).split("_")[0])
        date2 = pd.to_datetime(os.path.basename(v_files[i]).split("_")[1])
        difference_in_years = relativedelta(date2, date1).years
        difference_in_days = relativedelta(date2, date1).days / 365.25
        difference_in_years += difference_in_days
        deltaT_y[i] = difference_in_years
    return deltaT_y.astype(np.float32)


def np_slope_aspect(DEM, gridspacing):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    dx, dy = np.gradient(DEM, gridspacing)
    aspect = np.arctan2(-dy, dx)
    return np.rad2deg(
        np.arctan(np.sqrt(dx * dx + dy * dy))
    ), ArithmeticDegree_to_GeographicDegree((np.rad2deg(aspect)))


def convert_v_files(
    v_files, correlation_ar, height, width, ds_gt, epsg_code, gaussian_filter=False
):
    outdir = geotiffn + "v"
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    if gaussian_filter:
        outdir_gf = geotiffn + "v_gf"
        if not os.path.exists(outdir_gf):
            os.mkdir(outdir_gf)
    for i in tqdm.tqdm(range(len(v_files)), desc="Converting v files"):
        cfile = v_files[i]
        geotiff_fn = os.path.join(outdir, os.path.basename(cfile))
        deltaT = get_deltaT_from_filename(cfile)
        if os.path.exists(geotiff_fn):
            if gaussian_filter:
                bm, bm_ds_gt, bm_ds_proj, bm_epsg = load_offset_tif(cfile)
            else:
                continue
        else:
            oversampling = int(os.path.basename(cfile).split("_")[2][2:])
            matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
            bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
                cfile,
                matchingstep=matchingstep,
            )
            bm[correlation_ar[i, :, :] < c_threshold] = np.nan
            # filter bm results with slope. Use only slopes exceeding 5 degree
            bm[dem_slope < slope_threshold] = np.nan
            # filter with NDVI and NDSI mask
            ndvi_ndsi_mask = load_mask(cfile, bm.shape)
            bm[ndvi_ndsi_mask] = np.nan
            bm_nanmean = np.nanmean(bm)
            bm = bm - bm_nanmean
            bm = bm * (satellite_resolution_m / oversampling) / deltaT
            save_geotiff(
                geotiff_fn,
                bm,
                epsg_code,
                ds_gt,
                nan_value=np.nan,
            )
        if gaussian_filter:
            bm_gf = gaussian_filter_nan(
                bm, sigma=gaussian_sigma, truncate=gaussian_truncate
            )
            geotiff_fn = os.path.join(outdir_gf, os.path.basename(cfile))
            save_geotiff(
                geotiff_fn,
                bm_gf,
                epsg_code,
                ds_gt,
                nan_value=np.nan,
            )


def convert_u_files(
    u_files, correlation_ar, height, width, ds_gt, epsg_code, gaussian_filter=False
):
    outdir = geotiffn + "u"
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    if gaussian_filter:
        outdir_gf = geotiffn + "u_gf"
        if not os.path.exists(outdir_gf):
            os.mkdir(outdir_gf)
    for i in tqdm.tqdm(range(len(u_files)), desc="Converting u files"):
        cfile = u_files[i]
        geotiff_fn = os.path.join(outdir, os.path.basename(cfile))
        deltaT = get_deltaT_from_filename(cfile)
        if os.path.exists(geotiff_fn):
            if gaussian_filter:
                bm, bm_ds_gt, bm_ds_proj, bm_epsg = load_offset_tif(cfile)
            else:
                continue
        else:
            oversampling = int(os.path.basename(cfile).split("_")[2][2:])
            matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
            bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
                cfile,
                matchingstep=matchingstep,
            )
            bm[correlation_ar[i, :, :] < c_threshold] = np.nan
            # filter bm results with slope. Use only slopes exceeding 5 degree
            bm[dem_slope < slope_threshold] = np.nan
            # filter with NDVI and NDSI mask
            ndvi_ndsi_mask = load_mask(cfile, bm.shape)
            bm[ndvi_ndsi_mask] = np.nan
            bm_nanmean = np.nanmean(bm)
            bm = bm - bm_nanmean
            bm = bm * (satellite_resolution_m / oversampling) / deltaT
            save_geotiff(
                geotiff_fn,
                bm,
                epsg_code,
                ds_gt,
                nan_value=np.nan,
            )
        if gaussian_filter:
            bm_gf = gaussian_filter_nan(
                bm, sigma=gaussian_sigma, truncate=gaussian_truncate
            )
            geotiff_fn = os.path.join(outdir_gf, os.path.basename(cfile))
            save_geotiff(
                geotiff_fn,
                bm_gf,
                epsg_code,
                ds_gt,
                nan_value=np.nan,
            )


def load_dem_aspect_slope_files(dem_fname):
    logging.info("Loading DEM file %s" % dem_fname)
    dem, dem_gt, dem_proj, dem_epsg = load_Landsat_tif(dem_fname)
    # dem_slope, dem_aspect = np_slope_aspect(dem, dem_gt[1])
    # !gdaldem aspect COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    # !gdaldem slope COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_slope.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    #!gdaldem hillshade COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif COP15_DEM_NW_ARGENTINA_UTM20_P231R077_hs.tif -co COMPRESS=DEFLATE -co ZLEVEL=9
    dem_dir = os.path.dirname(dem_fname)
    dem_basename = os.path.basename(dem_fname).split(".")[0]
    aspect_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_aspect.tif"))
    aspect_fname = aspect_fname_lst[0]
    logging.info("Loading DEM-aspect file %s" % aspect_fname)
    dem_aspect, aspect_gt, aspect_proj, aspect_epsg = load_Landsat_tif(aspect_fname)
    dem_aspect[dem_aspect < 0] = np.nan
    slope_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_slope.tif"))
    slope_fname = slope_fname_lst[0]
    logging.info("Loading DEM-slope file %s" % slope_fname)
    dem_slope, slope_gt, slope_proj, slope_epsg = load_Landsat_tif(slope_fname)
    dem_slope[dem_slope < 0] = np.nan
    hs_fname_lst = glob.glob(os.path.join(dem_dir, dem_basename + "_hs.tif"))
    hs_fname = hs_fname_lst[0]
    logging.info("Loading DEM-hillshade file %s" % hs_fname)
    dem_hs, hs_gt, hs_proj, hs_epsg = load_Landsat_tif8bit(hs_fname)
    dem_hs = np.ma.masked_where(np.isnan(dem_slope), dem_hs)
    return dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs


def convert_correlation_files(correlation_files, geotiffn, ds_gt, epsg_code):
    outdir = geotiffn + "correlation"
    correlation_ar = np.empty((len(correlation_files), height, width), dtype=np.float32)
    correlation_ar.fill(np.nan)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    for i in tqdm.tqdm(
        range(len(correlation_files)), desc="Converting correlation tif files"
    ):
        geotiff_fn = os.path.join(outdir, os.path.basename(correlation_files[i]))
        if os.path.exists(geotiff_fn):
            foo_ds, _, _, _ = load_correlation_tif(geotiff_fn)
        else:
            matchingstep = int(os.path.basename(correlation_files[i]).split("_")[5][2:])
            foo_ds, correlation_gt, correlation_proj, epsg = (
                load_blockmatching_correlation_tif(correlation_files[i], matchingstep)
            )
            save_geotiff(
                geotiff_fn,
                foo_ds,
                epsg_code,
                ds_gt,
                nan_value=np.nan,
            )
        correlation_ar[i, :, :] = foo_ds
    return correlation_ar


def gaussian_filter_nan(displacement_my, sigma=2, truncate=4):
    # Gaussian Filter that ignores NaNs. First replaces NaNs with zeros and then uses a second run on a binary mask to remove the effect of 0.
    V = displacement_my.copy()
    V[np.isnan(displacement_my)] = 0
    VV = scipy.ndimage.gaussian_filter(
        V, sigma=sigma, truncate=truncate, mode="nearest"
    )
    W = 0 * displacement_my.copy() + 1
    W[np.isnan(displacement_my)] = 0
    WW = scipy.ndimage.gaussian_filter(
        W, sigma=sigma, truncate=truncate, mode="nearest"
    )
    return VV / WW


def get_file_dimensions(dirname):
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
    logging.info("Loading first u tif file to get array dimensions")
    foo_ds, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(u_files[0])
    epsg = int(osr.SpatialReference(wkt=foo_ds_proj).GetAttrValue("AUTHORITY", 1))
    height = foo_ds.shape[0]
    width = foo_ds.shape[1]
    foo_ds = None
    foo_ds_proj = None
    return height, width, foo_ds_gt, epsg


def create_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    logging.info("Data directory is %s" % (dirname))
    oversampling = int(os.path.basename(dirname).split("_")[1][2:])
    block_size = int(os.path.basename(dirname).split("_")[2][2:])
    search_radius = int(os.path.basename(dirname).split("_")[3][2:])
    matching_step = int(os.path.basename(dirname).split("_")[4][2:])
    outfile_correlation = []
    outfile_mask = []
    outfile_u = []
    outfile_v = []
    for i in range(len(date_pairs)):
        outfname_correlation = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_correlation.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_correlation = os.path.join(dirname, outfname_correlation)
        if not os.path.exists(outfname_correlation):
            logging.info("%s does not exists" % outfname_correlation)
        outfname_mask = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_mask.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_mask = os.path.join(dirname, outfname_mask)
        if not os.path.exists(outfname_mask):
            logging.info("%s does not exists" % outfname_mask)
        outfname_u = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_u.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_u = os.path.join(dirname, outfname_u)
        if not os.path.exists(outfname_u):
            logging.info("%s does not exists" % outfname_u)
        outfname_v = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_v.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_v = os.path.join(dirname, outfname_v)
        if not os.path.exists(outfname_v):
            logging.info("%s does not exists" % outfname_v)
        if (
            not os.path.exists(outfname_correlation)
            or not os.path.exists(outfname_mask)
            or not os.path.exists(outfname_u)
            or not os.path.exists(outfname_v)
        ):
            logging.info(
                "Not all correlation, mask, u, v files exists for that date. Not adding date %d_%d to list."
                % (date_pairs[i, 0], date_pairs[i, 1])
            )
        else:
            outfile_correlation.append(outfname_correlation)
            outfile_mask.append(outfname_mask)
            outfile_u.append(outfname_u)
            outfile_v.append(outfname_v)
    return outfile_correlation, outfile_mask, outfile_u, outfile_v


def count_nan_ar(u_ar, u_ar_masked):
    u_ar_nan = np.empty((u_ar.shape[0]), dtype=np.float32)
    u_ar_nan.fill(np.nan)
    u_ar_masked_nan = np.empty((u_ar_masked.shape[0]), dtype=np.float32)
    u_ar_masked_nan.fill(np.nan)
    for i in range(u_ar.shape[0]):
        u_ar_nan[i] = np.count_nonzero(~np.isnan(u_ar[i, :, :]))
        u_ar_masked_nan[i] = np.count_nonzero(~np.isnan(u_ar_masked[i, :, :]))
    return u_ar_nan, u_ar_masked_nan


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dirname = sys.argv[1]
    dirname_os01 = sys.argv[2]
    geotiffn = sys.argv[3]
    dem_fname = sys.argv[4]
    csv_fname = sys.argv[5]
    gaussian_sigma = 1
    gaussian_truncate = 3

    # python run_convert_block_matching_fromcsv.py  \
    # CORR_os05_bs91_sr06_ms05 \
    # CORR_os01_bs11_sr03_ms01/ \
    # CORR_os05_bs91_sr06_ms05_ \
    # COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif \
    # corr_dates_sd1_cc30
    # dirname = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs91_sr06_ms05"
    # dirname_os01 = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os01_bs11_sr03_ms01/"
    # geotiffn = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs91_sr06_ms05_"
    # dem_fname = (
    #     "/raid2-gpu2/bodo/LANDSAT/P231R077/COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    # )

    # dirname = "/work/bookhage/Landsat/P231R077/CORR_os05_bs91_sr06_ms05"
    # dirname_os01 = "/work/bookhage/Landsat/P231R077/CORR_os01_bs11_sr03_ms01/"
    # geotiffn = "/work/bookhage/Landsat/P231R077/CORR_os05_bs91_sr06_ms05_"
    # dem_fname = (
    #     "/work/bookhage/Landsat/P231R077/COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    # )
    # csv_fname = "corr_dates_sd1_cc30"

    satellite_resolution_m = 15
    c_threshold = 0.8
    slope_threshold = 1

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )
    outfile_correlation, outfile_mask, outfile_u, outfile_v = create_fnames_from_csv(
        csv_fname, dirname
    )
    height, width, ds_gt, epsg_code = get_file_dimensions(dirname_os01)
    logging.info("Loading %d correlation files" % len(outfile_correlation))
    correlation_ar = convert_correlation_files(
        outfile_correlation, geotiffn, ds_gt, epsg_code
    )
    convert_u_files(outfile_u, correlation_ar, height, width, ds_gt, epsg_code)
    convert_v_files(outfile_v, correlation_ar, height, width, ds_gt, epsg_code)
