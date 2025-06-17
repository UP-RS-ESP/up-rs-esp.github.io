from datetime import date
import numpy as np
import numba as nb
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from plot_hist import plot_hist
from scipy.stats import gaussian_kde as kde

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


def save_geotiff_bans(geotiff_fn, array, epsg_code, geotransform, nan_value):
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


def plot_stack_stats(dir_median, dir_var, mag_median, mag_wmean, stackfn):
    fig, ax = plt.subplots(2, 2, figsize=(16, 9), dpi=300)
    im0 = ax[0, 0].imshow(dir_median, vmin=0, vmax=360, cmap="hsv")
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="vertical")
    h.set_label("Direction (degree)")
    ax[0, 0].axis("off")
    im1 = ax[0, 1].imshow(
        dir_var,
        vmin=np.nanpercentile(dir_var, 2),
        vmax=np.nanpercentile(dir_var, 98),
        cmap="viridis",
    )
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="vertical")
    h.set_label("Direction variance (degree)")
    ax[0, 1].axis("off")
    im2 = ax[1, 0].imshow(
        mag_median,
        vmin=np.nanpercentile(mag_median, 2),
        vmax=np.nanpercentile(mag_median, 98),
        cmap="magma",
    )
    h = plt.colorbar(im2, ax=ax[1, 0], orientation="vertical")
    h.set_label("Displacement magnitude median (m/yr)")
    ax[1, 0].axis("off")
    im3 = ax[1, 1].imshow(
        mag_wmean,
        vmin=np.nanpercentile(mag_wmean, 2),
        vmax=np.nanpercentile(mag_wmean, 98),
        cmap="viridis",
    )
    h = plt.colorbar(im3, ax=ax[1, 1], orientation="vertical")
    h.set_label("Displacement magnitude weighted mean (m/yr)")
    ax[1, 1].axis("off")
    fig.suptitle("%s" % (stackfn))
    fig.tight_layout()
    fig.savefig(stackfn, dpi=300)
    plt.close()


def calc_stack_stats_np(stack):
    # not using this, too slow
    stack_mean = np.mean(stack, axis=0).astype(np.float32)
    stack_median = np.median(stack, axis=0).astype(np.float32)
    stack_var = np.var(stack, axis=0).astype(np.float32)
    stack_p25 = np.percentile(stack, 25, axis=0).astype(np.float32)
    stack_p75 = np.percentile(stack, 75, axis=0).astype(np.float32)
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75


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
                direction[i, j, k] = ArithmeticDegree_to_GeographicDegree(
                    np.rad2deg(np.arctan2(v_ar[i, j, k], u_ar[i, j, k]))
                )
                magnitude[i, j, k] = np.sqrt(v_ar[i, j, k] ** 2 + u_ar[i, j, k] ** 2)
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
    for i in nb.prange(u_ar.shape[0]):
        for j in nb.prange(u_ar.shape[1]):
            for k in nb.prange(u_ar.shape[2]):
                deltadirection[i, j, k] = np.abs(dem_aspect[j, k] - direction[i, j, k])
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

    velocity_magnitude = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_magnitude.fill(np.nan)
    velocity_direction = np.empty((u_ar.shape[1], u_ar.shape[2]), dtype=np.float32)
    velocity_direction.fill(np.nan)
    for i in nb.prange(u_ar.shape[1]):
        for j in nb.prange(u_ar.shape[2]):
            median_u = np.nanmedian(u_ar[:, i, j])
            median_v = np.nanmedian(v_ar[:, i, j])
            velocity_direction[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(np.arctan2(median_v, median_u))
            )
            velocity_magnitude[i, j] = np.sqrt(median_u**2 + median_v**2)
    return velocity_magnitude, velocity_direction


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


def plot_histograms(correlation_ar, correlation_files, png_fname):
    fig, ax = plt.subplots(1, 1, figsize=(16, 9), dpi=300, layout="constrained")
    bins = np.linspace(0, 1, 51)
    for i in range(correlation_ar.shape[0]):
        plot_hist(
            correlation_ar[i, :, :].ravel()[~np.isnan(correlation_ar[i, :, :].ravel())],
            bins=bins,
            log_bins=False,
            density=True,
            ax=ax,
            label=correlation_files[i],
        )
    ax.grid()
    ax.set_xlabel("Correlation coefficient")
    ax.set_ylabel("Density")
    plt.legend()
    fig.savefig(png_fname, dpi=300)


def load_mask(filename):
    date1 = os.path.basename(filename).split("_")[0]
    date2 = os.path.basename(filename).split("_")[1]
    fname = os.path.join(
        "/".join(os.path.dirname(filename).split("/")[:-1]),
        "MASKS",
        "%s_%s_NDSI_NDVI_mask.tif" % (date1, date2),
    )
    if os.path.exists(fname):
        mask_ds = gdal.Open(fname)
        mask_ar = np.array(mask_ds.GetRasterBand(1).ReadAsArray()).astype(np.bool_)
    else:
        logging.info("Mask %s does not exist." % (fname))
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


def plot_quantiles(x, y, xlabel, ylabel, png_fname):
    # make sure that both data have the same length and number of elements
    (xnan,) = np.where(~np.isnan(x))
    x = x[xnan]
    y = y[xnan]
    (ynan,) = np.where(~np.isnan(y))
    x = x[ynan]
    y = y[ynan]
    xnan = None
    ynan = None
    fig, ax = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    ax[0].plot(x, y, ",", color="k")
    ax[0].set_xlabel(xlabel)
    ax[0].set_ylabel(ylabel)
    ax[0].set_aspect("equal")
    # add red diagonal line indicate line of perfect match
    ax[0].plot([np.min(x), np.max(x)], [np.min(x), np.max(x)], "-", color="darkred")
    X, Y = np.mgrid[x.min() : x.max() : 50j, y.min() : y.max() : 50j]
    positions = np.vstack([X.ravel(), Y.ravel()])
    values = np.c_[x, y]
    gkernel = kde(values.T)
    Z = np.reshape(gkernel(positions).T, X.shape)
    ax[0].imshow(Z, cmap="Blues", alpha=0.2)
    ax[0].grid("on")

    x = np.sort(x)
    y = np.sort(y)
    quantiles = np.min([len(x), len(y)])
    quantiles = np.linspace(start=0, stop=1, num=100)
    x_quantiles = np.quantile(x, quantiles, method="linear")
    y_quantiles = np.quantile(y, quantiles, method="linear")
    x_quantiles = x_quantiles / np.max(x_quantiles)
    y_quantiles = y_quantiles / np.max(y_quantiles)
    ax[1].plot(x_quantiles, y_quantiles, ",", color="navy")
    ax[1].set_xlabel(xlabel)
    ax[1].set_ylabel(ylabel)
    ax[1].set_aspect("equal")
    # add red diagonal line indicate line of perfect match
    ax[1].plot([0, np.max(x_quantiles)], [0, np.max(y_quantiles)], "r-")
    ax[1].grid("on")
    fig.savefig(png_fname, dpi=300)


def load_v_files(dirname, correlation_ar, height, width):
    logging.info("Finding v tif files")
    v_files = glob.glob(os.path.join(dirname, "*_v.tif"))
    v_files.sort()
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading v files"):
        cfile = v_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        deltaT = get_deltaT_from_filename(cfile)
        # filter bm results with correlation coefficient. Keep only points above threshold
        correlation_nan = len(bm[correlation_ar[i, :, :] < c_threshold])
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        slope_nan = len(bm[dem_slope < slope_threshold])
        bm[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile)
        # if ndvi_ndsi_mask.shape != bm.shape:
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask, ndvi_ndsi_mask[-1]))
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask.T, ndvi_ndsi_mask.T[-1])).T
        ndvi_ndsi_nan = len(bm[ndvi_ndsi_mask == True])
        bm[ndvi_ndsi_mask == True] = np.nan
        # logging.info(
        #     "Set to Nan: Correlation %s (%2.1f %%), Slope %s (%2.1f %%), NDVI/NDSI %s (%2.1f %%)"
        #     % (
        #         f"{correlation_nan:,}",
        #         correlation_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #         f"{slope_nan:,}",
        #         slope_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #         f"{ndvi_ndsi_nan:,}",
        #         ndvi_ndsi_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #     )
        # )
        v_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return v_files, deltaT, v_ar


def load_u_files(dirname, correlation_ar, height, width):
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        deltaT = get_deltaT_from_filename(cfile)
        # filter bm results with correlation coefficient. Keep only points above threshold
        correlation_nan = len(bm[correlation_ar[i, :, :] < c_threshold])
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        slope_nan = len(bm[dem_slope < slope_threshold])
        bm[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile)
        # if ndvi_ndsi_mask.shape != bm.shape:
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask, ndvi_ndsi_mask[-1]))
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask.T, ndvi_ndsi_mask.T[-1])).T
        ndvi_ndsi_nan = len(bm[ndvi_ndsi_mask == True])
        bm[ndvi_ndsi_mask == True] = np.nan
        # logging.info(
        #     "Set to Nan: Correlation %s (%2.1f %%), Slope %s (%2.1f %%), NDVI/NDSI %s (%2.1f %%)"
        #     % (
        #         f"{correlation_nan:,}",
        #         correlation_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #         f"{slope_nan:,}",
        #         slope_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #         f"{ndvi_ndsi_nan:,}",
        #         ndvi_ndsi_nan / (bm.shape[0] * bm.shape[1]) * 100,
        #     )
        # )
        u_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return u_files, deltaT, u_ar


def load_dem_aspect_slope_files():
    logging.info("Loading DEM file %s" % dem_fname)
    dem, dem_gt, dem_proj, dem_epsg = load_Landsat_tif(dem_fname)
    # dem_slope, dem_aspect = np_slope_aspect(dem, dem_gt[1])

    # !gdaldem aspect COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    # !gdaldem slope COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_slope.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    aspect_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077_aspect.tif"
    logging.info("Loading DEM-aspect file %s" % aspect_fname)
    dem_aspect, aspect_gt, aspect_proj, aspect_epsg = load_Landsat_tif(aspect_fname)
    dem_aspect[dem_aspect < 0] = np.nan

    slope_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077_slope.tif"
    logging.info("Loading DEM-slope file %s" % slope_fname)
    dem_slope, slope_gt, slope_proj, slope_epsg = load_Landsat_tif(slope_fname)
    dem_slope[dem_slope < 0] = np.nan
    return dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope


def load_correlation_files(dirname, save_correlation_tif=False):
    logging.info("Finding correlation coefficient tif files")
    correlation_files = glob.glob(os.path.join(dirname, "*_correlation.tif"))
    correlation_files.sort()
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
    if save_correlation_tif == True:
        geotiff_fn = os.path.basename(dirname) + "_correlation_mean.tif"
        save_geotiff(
            geotiff_fn,
            np.nanmean(correlation_ar, axis=0),
            epsg,
            correlation_gt,
            nan_value=np.nan,
        )
        geotiff_fn = os.path.basename(dirname) + "_correlation_var.tif"
        save_geotiff(
            geotiff_fn,
            np.nanvar(correlation_ar, axis=0),
            epsg,
            correlation_gt,
            nan_value=np.nan,
        )
    return correlation_ar


def get_file_dimensions(dirname):
    logging.info("Finding u tif files")
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


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dirname = sys.argv[1]
    dirname_os01 = sys.argv[2]
    # stepsize = int(sys.argv[2])
    geotiffn = sys.argv[3]
    dem_fname = sys.argv[4]
    # python run_stack_block_matching_directory.py  \
    # CORR_os05_bs61_sr06_ms05/ \
    # CORR_os01_bs11_sr03_ms01/ \
    # CORR_os05_bs61_sr06_ms05_ \
    # COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif
    # dirname = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs61_sr06_ms05/"
    # dirname_os01 = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os01_bs11_sr03_ms01/"
    # stepsize = 15
    # geotiffn = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs61_sr06_ms05_"
    # dirname = "./"
    satellite_resolution_m = 15
    c_threshold = 0.9
    slope_threshold = 5
    deltadirection_threshold = 45
    # dem_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope = (
        load_dem_aspect_slope_files()
    )

    height, width, ds_gt, epsg_code = get_file_dimensions(dirname_os01)
    correlation_ar = load_correlation_files(dirname, save_correlation_tif=True)
    u_files, deltaT, u_ar = load_u_files(dirname, correlation_ar, height, width)
    v_files, deltaT, v_ar = load_v_files(dirname, correlation_ar, height, width)

    logging.info("Calculating velocity and direction for each multistep and resolution")
    direction, magnitude = calc_multistep_direction_velocity(u_ar, v_ar)
    logging.info("Calculating aspect and direction angle difference")
    deltadirection = calc_dem_aspect_direction_difference(dem_aspect, direction)
    logging.info(
        "Mask out pixels with an angle difference above %d degree"
        % deltadirection_threshold
    )
    u_ar, v_ar = mask_dem_aspect_direction(
        deltadirection, u_ar, v_ar, deltadirection_threshold=deltadirection_threshold
    )

    logging.info(
        "Calculating median velocity and direction for each date after masking"
    )
    velocity_magnitude, velocity_direction = calc_median_magnitude_direction(u_ar, v_ar)
    geotiff_outfn = geotiffn + "median_velocity_magnitude_m_yr.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_magnitude, epsg_code, ds_gt, nan_value=np.nan)
    geotiff_outfn = geotiffn + "median_velocity_direction.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_direction, epsg_code, ds_gt, nan_value=np.nan)

    # logging.info("Calculating mode velocity and direction for each after masking")
    # velocity_magnitude, velocity_direction = calc_mode_magnitude_direction(u_ar, v_ar)
    # geotiff_outfn = geotiffn + "mode_velocity_magnitude_m_yr.tif"
    # logging.info("Writing geotiff %s" % (geotiff_outfn))
    # save_geotiff(geotiff_outfn, velocity_magnitude, epsg_code, ds_gt, nan_value=np.nan)
    # geotiff_outfn = geotiffn + "mode_velocity_direction.tif"
    # logging.info("Writing geotiff %s" % (geotiff_outfn))
    # save_geotiff(geotiff_outfn, velocity_direction, epsg_code, ds_gt, nan_value=np.nan)

    logging.info("Calculating direction variance after masking")
    direction_variance = calc_direction_variance(u_ar, v_ar)
    geotiff_outfn = geotiffn + "variance_direction.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, direction_variance, epsg_code, ds_gt, nan_value=np.nan)
    logging.info("Calculating magnitude variance after masking")
    magnitude_variance = calc_magnitude_variance(u_ar, v_ar)
    geotiff_outfn = geotiffn + "variance_magnitude.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, magnitude_variance, epsg_code, ds_gt, nan_value=np.nan)
