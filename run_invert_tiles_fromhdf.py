from datetime import date
import numpy as np
import numba as nb
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from datetime import datetime
import pandas as pd
import matplotlib
import h5py

matplotlib.use("Agg")
import matplotlib.pyplot as plt

gdal.UseExceptions()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


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


def load_offset_tif_tile(fname, xoff=0, yoff=0, xsize=5000, ysize=5000):
    offset_ds = gdal.Open(fname)
    offset = np.array(
        offset_ds.GetRasterBand(1).ReadAsArray(xoff, yoff, xsize, ysize)
    ).astype("float32")
    offset_ds = None
    return offset


def load_offset_tif(fname):
    offset_ds = gdal.Open(fname)
    offset_ds_gt = offset_ds.GetGeoTransform()
    offset_ds_proj = offset_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=offset_ds_proj).GetAttrValue("AUTHORITY", 1))
    offset = np.array(offset_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    offset_ds = None
    return offset, offset_ds_gt, offset_ds_proj, epsg


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


@nb.njit(parallel=True)
def calc_dir_mag(v_ar, u_ar, deltaT_y, stepsize):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    uv_dir = np.empty(u_ar.shape, dtype=np.float32)
    uv_dir.fill(np.nan)
    uv_mag = np.empty(u_ar.shape, dtype=np.float32)
    uv_mag.fill(np.nan)
    for i in nb.prange(u_ar.shape[0]):
        uv_dir[i, :, :] = ArithmeticDegree_to_GeographicDegree(
            np.rad2deg(np.arctan2(v_ar[i, :, :], u_ar[i, :, :]))
        )
        uv_mag[i, :, :] = (
            np.sqrt(u_ar[i, :, :] ** 2 + v_ar[i, :, :] ** 2) * stepsize / deltaT_y[i]
        )
    return uv_dir, uv_mag


def calc_stack_stats_np(stack):
    # not using this, too slow
    stack_mean = np.mean(stack, axis=0).astype(np.float32)
    stack_median = np.median(stack, axis=0).astype(np.float32)
    stack_var = np.var(stack, axis=0).astype(np.float32)
    stack_p25 = np.percentile(stack, 25, axis=0).astype(np.float32)
    stack_p75 = np.percentile(stack, 75, axis=0).astype(np.float32)
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75


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


@nb.njit(parallel=True)
def calc_multistep_direction_velocity(u_ar, v_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    direction = np.empty(
        (u_ar.shape[0], u_ar.shape[1], u_ar.shape[2]), dtype=np.float32
    )
    direction.fill(np.nan)
    magnitude = np.empty(
        (u_ar.shape[0], u_ar.shape[1], u_ar.shape[2]), dtype=np.float32
    )
    magnitude.fill(np.nan)
    for i in nb.prange(u_ar.shape[0]):
        for j in nb.prange(u_ar.shape[1]):
            for k in nb.prange(u_ar.shape[2]):
                magnitude[i, j, k] = np.sqrt(v_ar[i, j, k] ** 2 + u_ar[i, j, k] ** 2)
                if magnitude[i, j, k] == 0:
                    continue
                else:
                    direction[i, j, k] = ArithmeticDegree_to_GeographicDegree(
                        np.rad2deg(np.arctan2(v_ar[i, j, k], u_ar[i, j, k]))
                    )
    return direction, magnitude


@nb.njit(parallel=True)
def mask_dem_aspect_direction(deltadirection, u_ar, v_ar, deltadirection_threshold=45):
    for i in nb.prange(deltadirection.shape[0]):
        for j in nb.prange(deltadirection.shape[1]):
            for k in nb.prange(deltadirection.shape[2]):
                if deltadirection[i, j, k] > deltadirection_threshold:
                    u_ar[i, j, k] = np.nan
                    v_ar[i, j, k] = np.nan
    return u_ar, v_ar


@nb.njit(parallel=True)
def calc_dem_aspect_direction_difference(dem_aspect, direction):
    deltadirection = np.empty(
        (u_ar.shape[0], u_ar.shape[1], u_ar.shape[2]), dtype=np.float32
    )
    deltadirection.fill(np.nan)
    for i in nb.prange(u_ar.shape[0]):
        for j in nb.prange(u_ar.shape[1]):
            for k in nb.prange(u_ar.shape[2]):
                if np.isnan(direction[i, j, k]):
                    continue
                angle1 = np.min(np.array([dem_aspect[j, k], direction[i, j, k]]))
                angle2 = np.max(np.array([dem_aspect[j, k], direction[i, j, k]]))
                if angle1 - angle2 < 0 and angle1 - angle2 > -180:
                    deltadirection[i, j, k] = np.abs(angle1 - angle2) % 360
                # elif angle1 - angle2 < -180:
                #     deltadirection[i, j, k] = (angle1 - angle2) % 360
                else:
                    deltadirection[i, j, k] = (angle1 - angle2) % 360
    return deltadirection


@nb.njit(parallel=True)
def calc_magnitude_variance(u_ar, v_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    stack_var = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    stack_var.fill(np.nan)
    for i in nb.prange(u_ar.shape[1]):
        for j in nb.prange(u_ar.shape[2]):
            var_u = np.nanvar(u_ar[:, i, j])
            var_v = np.nanvar(v_ar[:, i, j])
            stack_var[i, j] = np.sqrt(var_u**2 + var_v**2)
    return stack_var


@nb.njit(parallel=True)
def calc_direction_variance(u_ar, v_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    stack_var = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    stack_var.fill(np.nan)
    for i in nb.prange(u_ar.shape[1]):
        for j in nb.prange(u_ar.shape[2]):
            stack_var[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(
                    np.arctan2(np.nanvar(v_ar[:, i, j]), np.nanvar(u_ar[:, i, j]))
                )
            )
    return stack_var


@nb.njit(parallel=True)
def calc_correlation_stats(stack):
    stack_var = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_var.fill(np.nan)
    stack_mean = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_mean.fill(np.nan)
    stack_p25 = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_p25.fill(np.nan)
    stack_median = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_median.fill(np.nan)
    stack_p75 = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_p75.fill(np.nan)
    for i in nb.prange(stack.shape[1]):
        for j in nb.prange(stack.shape[2]):
            # the mean of correlation is done through the Fisher Z transform
            # the Fisher transform equals the inverse hyperbolic tangent
            stack_mean[i, j] = np.tanh(np.nanmean(np.arctanh(stack[:, i, j])))
            stack_var[i, j] = np.var(stack[:, i, j])
            stack_p25[i, j], stack_median[i, j], stack_p75[i, j] = np.percentile(
                stack[:, i, j], [25, 50, 75]
            )
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75


@nb.njit(parallel=True)
def calc_datepair_range(stack):
    stack_ptp = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_ptp.fill(np.nan)
    for i in nb.prange(stack.shape[1]):
        for j in nb.prange(stack.shape[2]):
            if np.all(np.isnan(stack[:, i, j])):
                continue
            if np.any(np.isnan(stack[:, i, j])):
                cvalue = stack[:, i, j][~np.isnan(stack[:, i, j])]
            else:
                cvalue = stack[:, i, j]
            stack_ptp[i, j] = np.ptp(cvalue)
    return stack_ptp


def calc_mode_magnitude_direction(u_ar, v_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    velocity_magnitude = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_magnitude.fill(np.nan)
    velocity_direction = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_direction.fill(np.nan)
    for i in tqdm.tqdm(range(u_ar.shape[1])):
        for j in nb.prange(u_ar.shape[2]):
            if np.all(np.isnan(u_ar[:, i, j])):
                continue
            vals, counts = np.unique(
                u_ar[:, i, j][~np.isnan(u_ar[:, i, j])], return_counts=True
            )
            index = np.argmax(counts)
            u_ar_mode = vals[index]
            vals, counts = np.unique(
                v_ar[:, i, j][~np.isnan(u_ar[:, i, j])], return_counts=True
            )
            index = np.argmax(counts)
            v_ar_mode = vals[index]
            velocity_direction[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(np.arctan2(v_ar_mode, u_ar_mode))
            )
            velocity_magnitude[i, j] = np.sqrt(u_ar_mode**2 + v_ar_mode**2)
    return velocity_magnitude, velocity_direction


@nb.njit(parallel=True)
def calc_median_magnitude_direction(u_ar, v_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

    median_u = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    median_u.fill(np.nan)
    median_v = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    median_v.fill(np.nan)
    velocity_magnitude = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_magnitude.fill(np.nan)
    velocity_direction = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_direction.fill(np.nan)
    velocity_nrm = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.uint8)
    velocity_nrm.fill(255)
    for i in nb.prange(u_ar.shape[1]):
        for j in nb.prange(u_ar.shape[2]):
            if np.all(np.isnan(u_ar[:, i, j])):
                # quick way to skip pixels that are all nan - the border pixels
                continue
            median_u[i, j] = np.nanmedian(u_ar[:, i, j])
            median_v[i, j] = np.nanmedian(v_ar[:, i, j])
            velocity_nrm[i, j] = np.count_nonzero(~np.isnan(u_ar[:, i, j]))
    # subtract mean from stack and subtract
    median_u_mean = np.nanmean(median_u)
    median_v_mean = np.nanmean(median_v)
    median_u = median_u - median_u_mean
    median_v = median_u - median_v_mean
    for i in nb.prange(median_u.shape[0]):
        for j in nb.prange(median_u.shape[1]):
            velocity_direction[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(np.arctan2(median_v[i, j], median_u[i, j]))
            )
            velocity_magnitude[i, j] = np.sqrt(
                median_u[i, j] ** 2 + median_v[i, j] ** 2
            )
    return velocity_magnitude, velocity_direction, velocity_nrm


@nb.njit(parallel=True)
def calc_date_stats(stack):
    stack_std = np.empty((stack.shape[0]), dtype=np.float32)
    stack_std.fill(np.nan)
    stack_var = np.empty((stack.shape[0]), dtype=np.float32)
    stack_var.fill(np.nan)
    stack_mean = np.empty((stack.shape[0]), dtype=np.float32)
    stack_mean.fill(np.nan)
    stack_p25 = np.empty((stack.shape[0]), dtype=np.float32)
    stack_p25.fill(np.nan)
    stack_median = np.empty((stack.shape[0]), dtype=np.float32)
    stack_median.fill(np.nan)
    stack_p75 = np.empty((stack.shape[0]), dtype=np.float32)
    stack_p75.fill(np.nan)
    for i in nb.prange(stack.shape[0]):
        stack_var[i] = np.nanvar(stack[i, :, :])
        stack_std[i] = np.nanstd(stack[i, :, :])
        stack_mean[i] = np.nanmean(stack[i, :, :])
        stack_p25[i], stack_median[i], stack_p75[i] = np.nanpercentile(
            stack[i, :, :], [25, 50, 75]
        )
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75, stack_std


@nb.njit(parallel=True)
def calc_stack_stats(stack, correlation_ar):
    stack_var = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_var.fill(np.nan)
    stack_mean = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_mean.fill(np.nan)
    stack_p25 = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_p25.fill(np.nan)
    stack_median = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_median.fill(np.nan)
    stack_p75 = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_p75.fill(np.nan)
    stack_weightedmean = np.empty((stack.shape[1], stack.shape[2]), dtype=np.float32)
    stack_weightedmean.fill(np.nan)
    for i in nb.prange(stack.shape[1]):
        for j in nb.prange(stack.shape[2]):
            stack_var[i, j] = np.var(stack[:, i, j])
            stack_mean[i, j] = np.mean(stack[:, i, j])
            stack_p25[i, j], stack_median[i, j], stack_p75[i, j] = np.percentile(
                stack[:, i, j], [25, 50, 75]
            )
            # calculating weighted average with np.average
            # heigher values have more importance / larger weights
            # np.average(v_ar[:,151,3059], weights=correlation_ar[:,151,3059]) is equals to
            # np.sum(v_ar[:,151,3059] * correlation_ar[:,151,3059]) / np.sum(correlation_ar[:,151,3059])
            # calculating weighted mean using correlation squared
            stack_weightedmean[i, j] = np.average(
                stack[:, i, j], weights=correlation_ar[:, i, j] ** 2
            )
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75, stack_weightedmean


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


def get_dates_deltaT_from_filename(filenames):
    date1_string = []
    date2_string = []
    date1 = []
    date2 = []
    deltaT_y = np.empty(len(filenames), dtype=np.float32)
    deltaT_y.fill(np.nan)
    for i in range(len(filenames)):
        date1_string.append(os.path.basename(filenames[i]).split("_")[0])
        date2_string.append(os.path.basename(filenames[i]).split("_")[1])
        date1.append(pd.to_datetime(os.path.basename(filenames[i]).split("_")[0]))
        date2.append(pd.to_datetime(os.path.basename(filenames[i]).split("_")[1]))
        difference_in_years = relativedelta(date2[i], date1[i]).years
        difference_in_days = relativedelta(date2[i], date1[i]).days / 365.25
        difference_in_years += difference_in_days
        deltaT_y[i] = difference_in_years
    return date1, date2, date1_string, date2_string, deltaT_y


def get_deltaT_from_filename(filename):
    date1 = pd.to_datetime(os.path.basename(filename).split("_")[0])
    date2 = pd.to_datetime(os.path.basename(filename).split("_")[1])
    difference_in_years = relativedelta(date2, date1).years
    difference_in_days = relativedelta(date2, date1).days / 365.25
    difference_in_years += difference_in_days
    deltaT_y = difference_in_years
    return (
        os.path.basename(filename).split("_")[0],
        os.path.basename(filename).split("_")[1],
        deltaT_y,
    )


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


def load_u_files_nomask(dirname, height, width):
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        # oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        u_ar[i, :, :] = bm
    return u_files, deltaT, u_ar


def load_u_files_tiles(u_files, xoff=0, yoff=0, xsize=5000, ysize=5000):
    height = ysize
    width = xsize
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    u_std = np.empty((len(u_files)), dtype=np.float32)
    u_std.fill(np.nan)
    u_mean = np.empty((len(u_files)), dtype=np.float32)
    u_mean.fill(np.nan)
    deltaT = np.empty(len(u_files), dtype=np.float32)
    date1_string = []
    date2_string = []
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        u = load_offset_tif_tile(cfile, xoff=xoff, yoff=yoff, xsize=xsize, ysize=ysize)
        date1, date2, deltaT[i] = get_deltaT_from_filename(cfile)
        date1_string.append(date1)
        date2_string.append(date2)
        u_ar[i, :, :] = u
    return deltaT, date1_string, date2_string, u_ar


def load_u_files(u_files):
    # open first file to get file dimension
    height, width, foo_ds_gt, epsg = get_file_dimensions_singlefile(u_files[0])
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    deltaT = np.empty(len(u_files), dtype=np.float32)
    u_std = np.empty(len(u_files), dtype=np.float32)
    date1_string = []
    date2_string = []
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        u, u_ds_gt, u_ds_proj, u_epsg = load_offset_tif(cfile)
        date1, date2, deltaT[i] = get_deltaT_from_filename(cfile)
        date1_string.append(date1)
        date2_string.append(date2)
        u_std[i] = np.nanstd(u)
        u_ar[i, :, :] = u
    return deltaT, date1_string, date2_string, u_ar, u_std


def load_mask_files(mask_files):
    # open first file to get file dimension
    mask_ds = gdal.Open(mask_files[0])
    height, width = (
        np.array(mask_ds.GetRasterBand(1).ReadAsArray()).astype(np.bool_).shape
    )
    mask_ar = np.zeros((len(mask_files), height, width), dtype=np.bool_)
    for i in tqdm.tqdm(range(len(mask_files)), desc="Loading mask files"):
        cfile = mask_files[i]
        mask_ds = gdal.Open(cfile)
        mask_ar[i, :, :] = np.array(mask_ds.GetRasterBand(1).ReadAsArray()).astype(
            np.bool_
        )
        # u_ar[ndvi_ndsi_mask] = np.nan
    return mask_ar


def apply_mask_files(u_ar, mask_ar):
    for i in tqdm.tqdm(range(len(u_ar)), desc="Applying mask file"):
        cu_ar = u_ar[i, :, :]
        cmask_ar = mask_ar[i, :, :]
        cu_ar[cmask_ar] = np.nan
        u_ar[i, :, :] = cu_ar
    return u_ar


def load_v_files(v_files):
    # open first file to get file dimension
    height, width, foo_ds_gt, epsg = get_file_dimensions_singlefile(v_files[0])
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    deltaT = np.empty(len(v_files), dtype=np.float32)
    v_std = np.empty(len(v_files), dtype=np.float32)
    date1_string = []
    date2_string = []
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading u files"):
        cfile = v_files[i]
        v, v_ds_gt, v_ds_proj, v_epsg = load_offset_tif(cfile)
        date1, date2, deltaT[i] = get_deltaT_from_filename(cfile)
        date1_string.append(date1)
        date2_string.append(date2)
        v_std[i] = np.nanstd(v)
        v_ar[i, :, :] = v
    return deltaT, date1_string, date2_string, v_ar, v_std


def load_v_files_tiles(v_files, xoff=0, yoff=0, xsize=5000, ysize=5000):
    height = ysize
    width = xsize
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    deltaT = np.empty(len(v_files), dtype=np.float32)
    date1_string = []
    date2_string = []
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading v files"):
        cfile = v_files[i]
        u = load_offset_tif_tile(cfile, xoff=xoff, yoff=yoff, xsize=xsize, ysize=ysize)
        date1, date2, deltaT[i] = get_deltaT_from_filename(cfile)
        date1_string.append(date1)
        date2_string.append(date2)
        v_ar[i, :, :] = u
    return deltaT, date1_string, date2_string, v_ar


def load_u_files_rotation(u_files, dirname, correlation_ar, height, width):
    u_pngs_dir = os.path.join(dirname, "u_corrected_pngs")
    if not os.path.exists(u_pngs_dir):
        os.mkdir(u_pngs_dir)
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    u_ar_ax0_mean = np.empty((len(u_files), width), dtype=np.float32)
    u_ar_ax0_mean.fill(np.nan)
    u_ar_ax0_mean_postcor = np.empty((len(u_files), width), dtype=np.float32)
    u_ar_ax0_mean_postcor.fill(np.nan)
    u_ar_ax1_mean = np.empty((len(u_files), height), dtype=np.float32)
    u_ar_ax1_mean.fill(np.nan)
    u_ar_ax1_mean_postcor = np.empty((len(u_files), height), dtype=np.float32)
    u_ar_ax1_mean_postcor.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        deltaT = get_deltaT_from_filename(cfile)
        # correlation_nan = len(bm[correlation_ar[i, :, :] < c_threshold])
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        bm_f[correlation_ar[i, :, :] < c_threshold] = np.nan
        # slope_nan = len(bm[dem_slope < slope_threshold])
        bm[dem_slope < slope_threshold] = np.nan
        bm_f[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile, bm.shape)
        bm[ndvi_ndsi_mask] = np.nan
        (
            bm_f,
            u_ar_ax0_mean[i, :],
            u_ar_ax0_mean_postcor[i, :],
            u_ar_ax1_mean[i, :],
            u_ar_ax1_mean_postcor[i, :],
        ) = correct_striping_rotate(
            bm,
            pngfn=os.path.join(
                u_pngs_dir, os.path.basename(cfile)[:-4] + "_striping_correction.png"
            ),
        )
        u_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return u_files, deltaT, u_ar


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


def load_correlation_files(
    correlation_files, geotiffn, ds_gt, epsg_code, save_correlation_tif=False
):
    correlation_ar = np.empty((len(correlation_files), height, width), dtype=np.float32)
    correlation_ar.fill(np.nan)
    for i in tqdm.tqdm(
        range(len(correlation_files)), desc="Loading correlation tif files"
    ):
        matchingstep = int(os.path.basename(correlation_files[i]).split("_")[5][2:])
        foo_ds, correlation_gt, correlation_proj, epsg = (
            load_blockmatching_correlation_tif(correlation_files[i], matchingstep)
        )
        correlation_ar[i, :, :] = foo_ds
    foo_ds = None
    # plot_histograms(correlation_ar, png_fname="Histogram_test.png")
    if save_correlation_tif:
        geotiff_fn = geotiffn + "correlation_mean.tif"
        save_geotiff(
            geotiff_fn,
            np.nanmean(correlation_ar, axis=0),
            epsg_code,
            ds_gt,
            nan_value=np.nan,
        )
        geotiff_fn = geotiffn + "correlation_var.tif"
        save_geotiff(
            geotiff_fn,
            np.nanvar(correlation_ar, axis=0),
            epsg_code,
            ds_gt,
            nan_value=np.nan,
        )
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


def get_file_dimensions_singlefile(u_file):
    foo_ds, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(u_file)
    epsg = int(osr.SpatialReference(wkt=foo_ds_proj).GetAttrValue("AUTHORITY", 1))
    height = foo_ds.shape[0]
    width = foo_ds.shape[1]
    foo_ds = None
    foo_ds_proj = None
    return height, width, foo_ds_gt, epsg


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


def create_MASK_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    mask_dir = os.path.dirname(dirname)
    mask_dir = os.path.join(mask_dir, "MASKS")
    logging.info("Data directory is %s" % (mask_dir))
    outfile_masks = []
    for i in range(len(date_pairs)):
        outfname_masks = "%d_%d_NDSI_NDVI_CLOUD_SHADOW_mask.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
        )
        outfname_masks = os.path.join(mask_dir, outfname_masks)
        if not os.path.exists(outfname_masks):
            logging.info("%s does not exists" % outfname_masks)
        else:
            outfile_masks.append(outfname_masks)
    return outfile_masks


def create_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    mask_dir = os.path.dirname(dirname)
    mask_dir = os.path.join(mask_dir, "MASKS")
    logging.info("Data directory is %s" % (dirname))
    oversampling = int(os.path.basename(dirname).split("_")[1][2:])
    block_size = int(os.path.basename(dirname).split("_")[2][2:])
    search_radius = int(os.path.basename(dirname).split("_")[3][2:])
    matching_step = int(os.path.basename(dirname).split("_")[4][2:])
    outfile_correlation = []
    outfile_u = []
    outfile_v = []
    outfile_masks = []
    for i in range(len(date_pairs)):
        outfname_correlation = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_correlation.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_correlation = os.path.join(
            dirname + "correlation", outfname_correlation
        )
        if not os.path.exists(outfname_correlation):
            logging.info("%s does not exists" % outfname_correlation)
        outfname_u = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_u.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_u = os.path.join(dirname + "u", outfname_u)
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
        outfname_v = os.path.join(dirname + "v", outfname_v)
        if not os.path.exists(outfname_v):
            logging.info("%s does not exists" % outfname_v)
        outfname_masks = "%d_%d_NDSI_NDVI_CLOUD_SHADOW_mask.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
        )
        outfname_masks = os.path.join(mask_dir, outfname_masks)
        if not os.path.exists(outfname_masks):
            logging.info("%s does not exists" % outfname_masks)
        if (
            not os.path.exists(outfname_correlation)
            or not os.path.exists(outfname_u)
            or not os.path.exists(outfname_v)
            or not os.path.exists(outfname_masks)
        ):
            logging.info(
                "Not all correlation, mask, u, v files exists for that date. Not adding date %d_%d to list."
                % (date_pairs[i, 0], date_pairs[i, 1])
            )
        else:
            outfile_correlation.append(outfname_correlation)
            outfile_u.append(outfname_u)
            outfile_v.append(outfname_v)
            outfile_masks.append(outfname_masks)
    return outfile_correlation, outfile_u, outfile_v, outfile_masks


def count_nan_ar(u_ar, u_ar_masked):
    u_ar_nan = np.empty((u_ar.shape[0]), dtype=np.float32)
    u_ar_nan.fill(np.nan)
    u_ar_masked_nan = np.empty((u_ar_masked.shape[0]), dtype=np.float32)
    u_ar_masked_nan.fill(np.nan)
    for i in range(u_ar.shape[0]):
        u_ar_nan[i] = np.count_nonzero(~np.isnan(u_ar[i, :, :]))
        u_ar_masked_nan[i] = np.count_nonzero(~np.isnan(u_ar_masked[i, :, :]))
    return u_ar_nan, u_ar_masked_nan


def Construction_dates_range_np(data):
    """
    Construction of the dates of the estimated displacement in X with an irregular temporal sampling (ILF).
    Code provided by Laurane Charrier.
    :param data: np.ndarray, an array where each line is (date1, date2, other elements) for which a velocity have been mesured
    :return: np.ndarray, the dates of the estimated displacement in X
    """

    dates = np.concatenate([data[:, 0], data[:, 1]])  # concatante date1 and date2
    dates = np.unique(dates)  # remove duplicates
    dates = np.sort(dates)  # Sort the dates
    return dates


def Construction_A_LF(dates, dates_range):
    """
    Construction of the design matix A in the formulation AX = B. Code provided by Laurane Charrier.

    :param dates: np array, where each line is (date1, date2) for which a velocity is computed (it corresponds to the original displacements)
    :param dates_range: list, dates of estimated displacemements in X

    :return: The design matrix A which represent the temporal closure of the displacement measurement network
    """
    # Search at which index in dates_range is stored each date in dates
    date1_indices = np.searchsorted(dates_range, dates[:, 0])
    date2_indices = np.searchsorted(dates_range, dates[:, 1]) - 1

    A = np.zeros((dates.shape[0], dates_range[1:].shape[0]), dtype="int32")
    for b in range(dates.shape[0]):
        A[b, date1_indices[b] : date2_indices[b] + 1] = 1

    return A


def mu_regularisation(regu: str, A: np.array, dates_range: np.array) -> np.array:
    """
    Compute the Tikhonov regularisation matrix. Code provided by Laurane Charrier.
    :param regu: str, type of regularization
    :param A: np array, design matrix
    :param dates_range: list, list of estimated dates
    :param ini: initial parameter (velocity and/or acceleration mean)
    :return mu: Tikhonov regularisation matrix
    """
    # First order Tikhonov regularisation
    if regu == 1:
        mu = np.identity(A.shape[1], dtype="float32")
        mu[np.arange(mu.shape[0] - 1) + 1, np.arange(mu.shape[0] - 1)] = -1
        mu /= np.diff(dates_range) / np.timedelta64(1, "D")
        mu = np.delete(mu, 0, axis=0)
    # First order Tikhonov regularisation, with an apriori on the acceleration
    elif regu == "1accelnotnull":
        mu = np.diag(np.full(A.shape[1], -1, dtype="float32"))
        mu[np.arange(A.shape[1] - 1), np.arange(A.shape[1] - 1) + 1] = 1
        mu /= np.diff(dates_range) / np.timedelta64(1, "D")
        mu = np.delete(mu, -1, axis=0)
    return mu


def to_datetime(date):
    """
    Converts a numpy datetime64 object to a python datetime object
    Input:
      date - a np.datetime64 object
    Output:
      DATE - a python datetime object
    """
    timestamp = (date - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
    return datetime.utcfromtimestamp(timestamp)


def create_design_matrix_cumulative_displacement(num_pairs, dates0, dates1):
    """
    Create designmatrix connecting the cumulative displacement vector and the displacement measured between each date pair.
    Args:
        num_pairs: integer value corresponding to the number of pairwise displacement measurements in network.
        dates0: array of reference dates.
        dates1: array of secondary dates.
    Returns:
        A: design matrix to be used in the inversion.
    """
    unique_dates = np.union1d(np.unique(dates0), np.unique(dates1))
    num_dates = len(unique_dates)
    datepair_list = []
    for i in range(len(dates0)):
        datepair_list.append(
            "%s_%s"
            % (
                datetime.strftime(dates0[i], "%Y%m%d"),
                datetime.strftime(dates1[i], "%Y%m%d"),
            )
        )
    A = np.zeros((num_pairs, num_dates), np.float32)
    date_list = list(unique_dates)
    date_list = [datetime.strftime(d, "%Y%m%d") for d in date_list]
    for i in range(num_pairs):
        ind1, ind2 = (date_list.index(d) for d in datepair_list[i].split("_"))
        A[i, ind1] = -1
        A[i, ind2] = 1
    # Remove reference date as it can not be resolved
    ref_date = datetime.strftime(min(dates0), "%Y%m%d")
    ind_r = date_list.index(ref_date)
    A = np.hstack((A[:, 0:ind_r], A[:, (ind_r + 1) :]))
    return A, date_list


def Inversion_A_LF(
    A, data, solver, Weight, mu, coef=1, ini=None, result_quality=None, verbose=False
):
    """
    Invert the system AX = B for one component of the velocity, using a given solver. Code provided by Laurane Charrier.

    :param A: Matrix of the temporal inversion system AX = B
    :param data: np array, displacement observation B
    :param solver: 'LSMR', 'LSMR_ini', 'LS', 'LS_bounded', 'LSQR'
    :param Weight: Weight, =1 for Ordinary Least Square
    :param mu: regularization matrix
    :param coef: Coef of Tikhonov regularization
    :param ini: np array, Initialization of the inversion
    :param: result_quality: None or list of str, which can contain 'Norm_residual' to determine the L2 norm of the residuals from the last inversion, 'X_contribution' to determine the number of Y observations which have contributed to estimate each value in X (it corresponds to A.dot(weight))
    :param regu : str, type of regularization

    :return X: The ILF temporal inversion of AX = Y using the given solver
    :return residu_norm: Norm of the residual (when showing the L curve)
    """

    v = data
    D_regu = np.zeros(mu.shape[0])
    F_regu = np.multiply(coef, mu)
    if isinstance(Weight, int):
        if Weight == 1:
            Weight = np.ones(
                v.shape[0]
            )  # there is no weight, it corresponds to Ordinary Least Square
    if solver == "LSMR":
        F = np.vstack(
            [np.multiply(Weight[Weight != 0][:, np.newaxis], A[Weight != 0]), F_regu]
        ).astype("float")
        D = np.hstack(
            [np.multiply(Weight[Weight != 0], v[Weight != 0]), D_regu]
        ).astype("float")
        F = sp.csc_matrix(
            F
        )  # column-scaling so that each column have the same euclidian norme (i.e. 1)
        X = sp.linalg.lsmr(F, D)[
            0
        ]  # If atol or btol is None, a default value of 1.0e-6 will be used. Ideally, they should be estimates of the relative error in the entries of A and b respectively.

    elif solver == "LSMR_ini":  # 50ms
        # 16.7 ms ± 141 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
        condi = Weight != 0
        W = Weight[condi]
        F = sp.csc_matrix(
            np.vstack([np.multiply(W[:, np.newaxis], A[condi]), F_regu])
        )  # stack ax and regu, and remove rows with only 0
        D = np.hstack(
            [np.multiply(W, v[condi]), D_regu]
        )  # stack ax and regu, and remove rows with only

        if ini.shape[0] == 2:  # if only the average of the entire time series
            x0 = np.full(len(A.shape[1]) - 1, ini, dtype="float32")
        else:
            x0 = ini
        X = sp.linalg.lsmr(F, D, x0=x0)[0]

    if (
        result_quality is not None and "Norm_residual" in result_quality
    ):  # to show the L_curve
        R_lcurve = (
            F.dot(X) - D
        )  # 50.7 µs ± 327 ns per loop (mean ± std. dev. of 7 runs, 10,000 loops each)
        residu_norm = [
            np.linalg.norm(
                R_lcurve[: np.multiply(Weight[Weight != 0], v[Weight != 0]).shape[0]],
                ord=2,
            ),
            np.linalg.norm(
                R_lcurve[np.multiply(Weight[Weight != 0], v[Weight != 0]).shape[0] :]
                / coef,
                ord=2,
            ),
        ]
    else:
        residu_norm = None
    return X, residu_norm


def solve_matrix_system(A, B, weights=None):
    """
    Solve matrix system of the form AX = B using least squares without a regularization term.
    Args:
        A: design matrix
        B: vector storing pairwise displacement measurements
        weights: vector with the weight to be assigned to every pairwise displacement measurement.
    Returns:
        ts: inverted time series
    """
    if weights is not None:
        weights = np.diag(weights).astype(np.float64)
        A = np.dot(weights, A.astype(np.float64))
        B = np.dot(weights, B)
    num_dates = A.shape[1] + 1
    ts = np.zeros(
        (num_dates, 1), dtype=np.float32
    )  # intialize empty output time series
    B = B.astype(np.float32)
    X, residuals, _, _ = np.linalg.lstsq(A.astype(np.float32), B)
    ts[1:, 0] = X.astype(np.float32)  # first displacement will be 0
    return ts[:, 0]


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dirprefix = sys.argv[1]
    dem_fname = sys.argv[2]
    csv_fname = sys.argv[3]
    plot_pngs = False
    plot_clip_pngs = False
    calc_mode = False
    # python run_stack_block_matching_fromcsv.py  \
    # CORR_os05_bs91_sr06_ms05 \
    # CORR_os01_bs11_sr03_ms01/ \
    # CORR_os05_bs91_sr06_ms05_ \
    # COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif \
    # corr_dates_sd1_cc30_short
    dirprefix = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs91_sr06_ms05_"
    dem_fname = (
        "/raid2-gpu2/bodo/LANDSAT/P231R077/COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    )
    dem_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    csv_fname = "corr_dates_sd1_cc29"
    geotiffn = os.path.basename(dirprefix)

    # dem_fname = (
    #     "/work/bookhage/Landsat/P231R077/COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    # )
    # csv_fname = "corr_dates_sd1_cc30_short"

    satellite_resolution_m = 15
    deltadirection_threshold = 45
    gaussian_sigma = 1
    gaussian_truncate = 3

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )
    outfile_correlation, outfile_u, outfile_v, outfile_masks = create_fnames_from_csv(
        csv_fname, dirprefix
    )
    # outfile_masks = create_MASK_fnames_from_csv(csv_fname, dirprefix)
    # logging.info("Loading %d full u files" % len(outfile_u))
    # deltaT, date1_string, date2_string, u_ar, u_std = load_u_files(outfile_u)
    # combine into pd table and write to csv

    u_stats_df = pd.read_csv("corr_dates_sd1_cc29_u_stats.csv", index_col="filenr")
    u_stats_df["date1"] = pd.to_datetime(u_stats_df.date1, format="%Y-%m-%d")
    u_stats_df["date2"] = pd.to_datetime(u_stats_df.date2, format="%Y-%m-%d")
    float64_cols = list(u_stats_df.select_dtypes(include="float64"))
    u_stats_df[float64_cols] = u_stats_df[float64_cols].astype("float32")

    logging.info("Loading %d tiled u and v files" % len(outfile_u))
    height, width, foo_ds_gt, epsg = get_file_dimensions_singlefile(
        outfile_u[0]
    )  # the dimensions should be the same as the DEM

    # load each tile area separately, perform stacking and filtering and write output. Merge in next step.
    tile_size = 5000
    xtiles = int(np.ceil(dem.shape[1] / tile_size))
    ytiles = int(np.ceil(dem.shape[0] / tile_size))
    for i in range(xtiles):
        for j in range(ytiles):
            logging.info(
                "Processing tile %02d/%02d" % ((i + j) + 1, (xtiles * ytiles) - 1)
            )
            xoff = tile_size * i
            yoff = tile_size * j
            if xoff + tile_size > dem.shape[1]:
                xsize = dem.shape[1] - xoff
            else:
                xsize = tile_size
            if yoff + tile_size > dem.shape[0]:
                ysize = dem.shape[0] - yoff
            else:
                ysize = tile_size

            # hdf_fname = dirprefix + "u_stats_tile_x%02d_y%02d.h5" % (i, j)
            # logging.info("Loading u stats tile %s" % hdf_fname)
            # f = h5py.File(hdf_fname, 'r')['mydataset']

            hdf_fname = dirprefix + "u_ts_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Loading u array time series %s" % hdf_fname)
            u_ar = np.asarray(h5py.File(hdf_fname, "r")["u_ar"])
            B = u_ar[:, 1, 1] * u_stats_df["deltaT_y"].to_numpy()
            (B_idx,) = np.where(~np.isnan(B))
            B = B[B_idx]
            # convert numpy datetime64 to datetime object before creating design matrix
            dates0 = [to_datetime(d) for d in u_stats_df["date1"]]
            dates0 = np.asarray(dates0)[B_idx]
            dates1 = [to_datetime(d) for d in u_stats_df["date2"]]
            dates1 = np.asarray(dates1)[B_idx]
            A, date_list = create_design_matrix_cumulative_displacement(
                len(B), dates0, dates1
            )
            ts = solve_matrix_system(
                A, B, weights=1 / u_stats_df["uvar"].to_numpy()[B_idx]
            )

            # inversion with regularization term
            data = np.vstack((dates0, dates1)).T
            sample_dates = np.unique(np.hstack((dates0, dates1)))
            sample_dates = np.sort(sample_dates)

            dates_range = Construction_dates_range_np(data)
            A = Construction_A_LF(data, dates_range)
            nIslands = np.min(A.shape) - np.linalg.matrix_rank(A)
            print(f"Number of groups in network: {nIslands +1}")
            print("Solving the inversion including a regularization term ...")
            mu = mu_regularisation(regu=1, A=A, dates_range=sample_dates)

            if weightcol is not None:
                Weight = net[weightcol].values
            else:
                Weight = 1
            timeseries, normresidual = Inversion_A_LF(
                A,
                B,
                solver="LSMR",
                Weight=Weight,
                mu=mu,
                coef=1,
                ini=None,
                result_quality=None,
                verbose=False,
            )
            timeseries_cumulative = np.cumsum(
                timeseries
            )  # build the cumulative time series bc LF design matrix solves for displacement at each time step
            timeseries_cumulative = np.insert(
                timeseries_cumulative, 0, 0, axis=0
            )  # set first date to zero

            logging.info("Load %d u files" % len(outfile_u))
            deltaT_y, date1_string, date2_string, u_ar = load_u_files_tiles(
                outfile_u, xoff=xoff, yoff=yoff, xsize=xsize, ysize=ysize
            )
            logging.info("Load %d v files" % len(outfile_v))
            deltaT_y, date1_string, date2_string, v_ar = load_v_files_tiles(
                outfile_v, xoff=xoff, yoff=yoff, xsize=xsize, ysize=ysize
            )
            logging.info("Calculating velocity and direction for each date")
            direction, magnitude = calc_multistep_direction_velocity(u_ar, v_ar)
            logging.info("Calculating aspect and direction angle difference")
            deltadirection = calc_dem_aspect_direction_difference(
                dem_aspect[yoff : yoff + ysize, xoff : xoff + xsize], direction
            )
            # deltadirection_median = np.nanmedian(deltadirection)
            # geotiff_outfn = geotiffn + "aspect_direction_difference_median.tif"
            # logging.info("Writing geotiff %s" % (geotiff_outfn))
            # save_geotiff(
            #     geotiff_outfn, deltadirection_median, epsg_code, ds_gt, nan_value=np.nan
            # )
            logging.info(
                "Mask out pixels with an angle difference above %d degree for each date"
                % deltadirection_threshold
            )
            u_ar, v_ar = mask_dem_aspect_direction(
                deltadirection,
                u_ar,
                v_ar,
                deltadirection_threshold=deltadirection_threshold,
            )
            logging.info("Calculating mean and std. dev. velocity for each date")
            u_mean, u_median, u_var, u_p25, u_p75, u_std = calc_date_stats(u_ar)
            hdf_fname = dirprefix + "u_stats_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Writing u stats tile %s" % hdf_fname)
            with h5py.File(hdf_fname, "w") as f:
                f.create_dataset(
                    "u_mean",
                    data=u_mean,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "u_median",
                    data=u_median,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "u_var",
                    data=u_var,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "u_p25",
                    data=u_p25,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "u_p75",
                    data=u_p75,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "u_stdn",
                    data=u_std,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
            v_mean, v_median, v_var, v_p25, v_p75, v_std = calc_date_stats(v_ar)
            hdf_fname = dirprefix + "v_stats_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Writing v stats tile %s" % hdf_fname)
            with h5py.File(hdf_fname, "w") as f:
                f.create_dataset(
                    "v_mean",
                    data=v_mean,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "v_median",
                    data=v_median,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "v_var",
                    data=v_var,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "v_p25",
                    data=v_p25,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "v_p75",
                    data=v_p75,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "v_stdn",
                    data=v_std,
                    dtype=np.float32,
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
            # logging.info("Calculating mean velocity from stack and subtract ")
            # velocity_magnitude, velocity_direction, velocity_nrm = (
            #     calc_median_magnitude_direction(u_ar, v_ar)
            # )
            logging.info(
                "Calculating median velocity and direction after aspect masking"
            )
            velocity_magnitude, velocity_direction, velocity_nrm = (
                calc_median_magnitude_direction(u_ar, v_ar)
            )
            hdf_fname = dirprefix + "velocity_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Writing velocity tile %s" % hdf_fname)
            with h5py.File(hdf_fname, "w") as f:
                f.create_dataset(
                    "velocity_magnitude",
                    data=velocity_magnitude,
                    dtype=np.dtype(velocity_magnitude[0, 0]),
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "velocity_direction",
                    data=velocity_direction,
                    dtype=np.dtype(velocity_direction[0, 0]),
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
                f.create_dataset(
                    "velocity_nrm",
                    data=velocity_nrm,
                    dtype=np.dtype(velocity_nrm[0, 0]),
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
            hdf_fname = dirprefix + "u_ts_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Writing u array time series %s" % hdf_fname)
            with h5py.File(hdf_fname, "w") as f:
                f.create_dataset(
                    "u_ar",
                    data=u_ar,
                    dtype=np.dtype(u_ar[0, 0, 0]),
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
            hdf_fname = dirprefix + "v_ts_tile_x%02d_y%02d.h5" % (i, j)
            logging.info("Writing v array time series%s" % hdf_fname)
            with h5py.File(hdf_fname, "w") as f:
                f.create_dataset(
                    "v_ar",
                    data=v_ar,
                    dtype=np.dtype(v_ar[0, 0, 0]),
                    compression="gzip",
                    compression_opts=7,
                    chunks=True,
                )
            del (
                deltaT_y,
                date1_string,
                date2_string,
                u_ar,
                v_ar,
                velocity_magnitude,
                velocity_direction,
                velocity_nrm,
                direction,
                magnitude,
                deltadirection,
            )

            if i == 0 and j == 0:
                hdf_fname = dirprefix + "dates_data.h5"
                logging.info("Writing date data %s" % hdf_fname)
                with h5py.File(hdf_fname, "w") as f:
                    f.create_dataset(
                        "deltaT_y",
                        data=deltaT_y,
                        dtype=np.dtype(deltaT_y[0]),
                        compression="gzip",
                        compression_opts=7,
                        chunks=True,
                    )
                    f.create_dataset(
                        "date1_string",
                        data=date1_string,
                        compression="gzip",
                        compression_opts=7,
                        chunks=True,
                    )
                    f.create_dataset(
                        "date2_string",
                        data=date2_string,
                        compression="gzip",
                        compression_opts=7,
                        chunks=True,
                    )
