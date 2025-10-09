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
def calc_direction_stats(stack, u_ar, v_ar, correlation_ar):
    def ArithmeticDegree_to_GeographicDegree(angle):
        return (-(angle - 90)) % 360

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
            stack_var[i, j] = np.rad2deg(
                np.arctan2(np.var(v_ar[:, i, j]), np.var(u_ar[:, i, j]))
            )
            stack_mean[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(np.arctan2(np.mean(v_ar[:, i, j]), np.mean(u_ar[:, i, j])))
            )
            stack_median[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(
                    np.arctan2(np.median(v_ar[:, i, j]), np.median(u_ar[:, i, j]))
                )
            )
            stack_weightedmean[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(
                    np.arctan2(
                        np.average(v_ar[:, i, j], correlation_ar[:, i, j] ** 2),
                        np.average(u_ar[:, i, j], correlation_ar[:, i, j] ** 2),
                    )
                )
            )
            stack_p25[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(
                    np.arctan2(
                        np.percentile(v_ar[:, i, j], 25),
                        np.percentile(u_ar[:, i, j], 25),
                    )
                )
            )
            stack_p75[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(
                    np.arctan2(
                        np.percentile(v_ar[:, i, j], 75),
                        np.percentile(u_ar[:, i, j], 75),
                    )
                )
            )
    return stack_mean, stack_median, stack_var, stack_p25, stack_p75, stack_weightedmean


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


def load_v_files(correlation_ar, height, width):
    logging.info("Finding v tif files")
    v_files = glob.glob(os.path.join(dirname, "*", "%s*_v.tif" % date_pair))
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
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        bm[dem_slope < slope_threshold] = np.nan
        v_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return v_files, deltaT, v_ar


def load_u_files(correlation_ar, height, width):
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*", "%s*_u.tif" % date_pair))
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
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        bm[dem_slope < slope_threshold] = np.nan
        u_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return u_files, deltaT, u_ar


def load_dem_aspect_slope_files():
    logging.info("Loading DEM file %s" % dem_fname)
    dem, dem_gt, dem_proj, dem_epsg = load_Landsat_tif(dem_fname)
    # dem_slope, dem_aspect = np_slope_aspect(dem, dem_gt[1])

    # !gdaldem aspect COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    # !gdaldem slope COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_slope.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    aspect_fname = "COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif"
    logging.info("Loading DEM-aspect file %s" % aspect_fname)
    dem_aspect, aspect_gt, aspect_proj, aspect_epsg = load_Landsat_tif(aspect_fname)
    dem_aspect[dem_aspect < 0] = np.nan

    slope_fname = "COP15_DEM_NW_ARGENTINA_UTM20_slope.tif"
    logging.info("Loading DEM-slope file %s" % slope_fname)
    dem_slope, slope_gt, slope_proj, slope_epsg = load_Landsat_tif(slope_fname)
    dem_slope[dem_slope < 0] = np.nan
    return dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope


def load_correlation_files(date_pair, save_correlation_tif=False):
    logging.info("Finding correlation coefficient tif files")
    correlation_files = glob.glob(
        os.path.join(dirname, "*", "%s*_correlation.tif" % date_pair)
    )
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
        geotiff_fn = "correlation_%s_mean.tif" % date_pair
        save_geotiff(
            geotiff_fn,
            np.nanmean(correlation_ar, axis=0),
            epsg,
            correlation_gt,
            nan_value=np.nan,
        )
        geotiff_fn = "correlation_%s_var.tif" % date_pair
        save_geotiff(
            geotiff_fn,
            np.nanvar(correlation_ar, axis=0),
            epsg,
            correlation_gt,
            nan_value=np.nan,
        )
    return correlation_ar


def get_file_dimensions():
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*", "%s*_u.tif" % date_pair))
    u_files.sort()
    logging.info("Loading first u tif file to get array dimensions")
    foo_ds, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(u_files[0])
    height = foo_ds.shape[0]
    width = foo_ds.shape[1]
    foo_ds = None
    foo_ds_gt = None
    foo_ds_proj = None
    return height, width


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dirname = sys.argv[1]
    stepsize = int(sys.argv[2])
    geotiffn = sys.argv[3]

    # dirname = "/raid2-gpu2/bodo/LANDSAT/P232R077/BLOCKMATCHING_os01_bs31_sr03/"
    # stepsize = 15
    # geotiffn = "/raid2-gpu2/bodo/LANDSAT/P232R077/CROP/LC08_L1TP_232077_20141102_20200910_02_T1_B8.TIF"
    dirname = "./"
    satellite_resolution_m = 15
    c_threshold = 0.9
    slope_threshold = 5
    deltadirection_threshold = 45
    dem_fname = "COP15_DEM_NW_ARGENTINA_UTM20.tif"

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope = (
        load_dem_aspect_slope_files()
    )

    date_pair = "20130601_20230605"
    height, width = get_file_dimensions()
    correlation_ar = load_correlation_files(date_pair, save_correlation_tif=False)
    u_files, deltaT, u_ar = load_u_files(correlation_ar, height, width)
    v_files, deltaT, v_ar = load_v_files(correlation_ar, height, width)

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
        "Calculating velocity and direction for each multistep and resolution after masking"
    )
    direction, magnitude = calc_multistep_direction_velocity(u_ar, v_ar)

    plot_quantiles(
        x=u_ar[0, :, :].ravel(),
        y=u_ar[1, :, :].ravel(),
        xlabel="u displacement (m/y) for CORR_os01_bs11_sr03_ms01",
        ylabel="u displacement (m/y) for CORR_os01_bs21_sr03_ms01",
        png_fname="u_displacement_os01_bs11_vs_21_sr03_ms01.png",
    )

    # Calculate range of values for each pixel
    u_ptp = calc_datepair_range(u_ar)

    logging.info("Getting time difference in years from filenames")
    deltaT_y = np.float32(get_deltaT_from_filename(u_files))

    logging.info("Calculating statistics for correlation coefficients (numba)")
    start = time.time()
    (
        correlation_mean,
        correlation_median,
        correlation_var,
        correlation_p25,
        correlation_p75,
    ) = calc_correlation_stats(correlation_ar)
    end = time.time()
    length_s = end - start
    logging.info("Calculating statistics (numba) took %d seconds" % (length_s))

    logging.info("Calculating velocity direction and magnitude for every pair (numba)")
    uv_dir, uv_mag = calc_dir_mag(v_ar, u_ar, deltaT_y, stepsize=stepsize)
    logging.info(
        "Calculating velocity direction mean, median, variance, 25perc, 75perc (numba)"
    )
    start = time.time()
    dir_mean, dir_median, dir_var, dir_p25, dir_p75, dir_wmean = calc_direction_stats(
        uv_dir,
        u_ar,
        v_ar,
        correlation_ar,
    )
    end = time.time()
    length_s = end - start
    logging.info("Calculating statistics (numba) took %d seconds" % (length_s))

    logging.info(
        "Calculating velocity magnitude mean, median, variance, 25perc, 75perc (numba)"
    )
    start = time.time()
    mag_mean, mag_median, mag_var, mag_p25, mag_p75, mag_wmean = calc_stack_stats(
        uv_mag, correlation_ar
    )
    end = time.time()
    length_s = end - start
    logging.info("Calculating statistics (numba) took %d seconds" % (length_s))

    # not using numpy, because it is way too slow.
    # logging.info('Calculating stack mean, median, variance, 25perc, 75perc (numpy)')
    # start = time.time()
    # stack_mean_np, stack_median_np, stack_var_np, stack_p25_np, stack_p75_np = calc_stack_stats_np(stack)
    # end = time.time()
    # length_s = end - start
    # logging.info("Calculating statistics (numpy) took %d seconds" % (length_s))

    if dirname.split("/")[-1] == "":
        stack_basename = dirname.split("/")[-2]
        stackfn = stack_basename + "_unmasked_dir_mag.png"
    else:
        stack_basename = dirname.split("/")[-1]
        stackfn = stack_basename + "_unmasked_dir_mag.png"

    logging.info("Plotting stack to %s" % stackfn)
    plot_stack_stats(dir_median, dir_var, mag_median, mag_wmean, stackfn)

    logging.info("Extract geotiff information from %s" % (geotiffn))
    gt, proj, epsg_code, ys, xs = get_geotiff_info(geotiffn)

    geotif_outfn = stack_basename + "_unmasked_correlation_mean.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, correlation_mean, int(epsg_code), gt, nan_value=np.nan)

    # geotif_outfn = stack_basename + "_unmasked_vel_my_median.tif"
    # logging.info("Writing geotiff %s" % (geotif_outfn))
    # save_geotiff(geotif_outfn, mag_median, int(epsg_code), gt, nan_value=np.nan)
    #
    # geotif_outfn = stack_basename + "_unmasked_vel_my_wmean.tif"
    # logging.info("Writing geotiff %s" % (geotif_outfn))
    # save_geotiff(geotif_outfn, mag_wmean, int(epsg_code), gt, nan_value=np.nan)
    #
    # geotif_outfn = stack_basename + "_unmasked_vel_my_var.tif"
    # logging.info("Writing geotiff %s" % (geotif_outfn))
    # save_geotiff(geotif_outfn, mag_var, int(epsg_code), gt, nan_value=np.nan)
    #
    # geotif_outfn = stack_basename + "_unmasked_direction_median.tif"
    # logging.info("Writing geotiff %s" % (geotif_outfn))
    # save_geotiff(geotif_outfn, dir_median, int(epsg_code), gt, nan_value=np.nan)
    #
    # geotif_outfn = stack_basename + "_unmasked_direction_var.tif"
    # logging.info("Writing geotiff %s" % (geotif_outfn))
    # save_geotiff(geotif_outfn, dir_var, int(epsg_code), gt, nan_value=np.nan)

    correlation_mean09_idxx, correlation_mean09_idxy = np.where(correlation_mean > 0.9)
    correlation_belowmean09_idxx, correlation_belowmean09_idxy = np.where(
        correlation_mean <= 0.9
    )
    logging.info(
        "Masking stack by correlation 0.9 - removing %s pixels"
        % (f"{len(correlation_belowmean09_idxx):,}",)
    )
    dir_var[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan
    dir_median[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan
    mag_median[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan
    mag_var[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan
    mag_wmean[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan
    correlation_mean[correlation_mean09_idxx, correlation_mean09_idxy] = np.nan

    dir_belowvar20_idxx, dir_belowvar20_idxy = np.where(dir_var <= 20)
    dir_var20_idxx, dir_var20_idxy = np.where(dir_var > 20)
    logging.info(
        "Masking stack by direction - removing %s pixels"
        % (f"{len(dir_var20_idxx):,}",)
    )
    dir_var[dir_var20_idxx, dir_var20_idxy] = np.nan
    dir_median[dir_var20_idxx, dir_var20_idxy] = np.nan
    mag_median[dir_var20_idxx, dir_var20_idxy] = np.nan
    mag_var[dir_var20_idxx, dir_var20_idxy] = np.nan
    mag_wmean[dir_var20_idxx, dir_var20_idxy] = np.nan
    correlation_mean[dir_var20_idxx, dir_var20_idxy] = np.nan

    # logging.info("Masking stack by velocty")
    # mag_var3_idxx, mag_var3_idxy = np.where(mag_var > 3)
    # dir_median[mag_var3_idxx, mag_var3_idxy] = np.nan
    # dir_var[mag_var3_idxx, mag_var3_idxy] = np.nan
    # mag_median[mag_var3_idxx, mag_var3_idxy] = np.nan
    # mag_var[mag_var3_idxx, mag_var3_idxy] = np.nan

    stackfn = stack_basename + "_masked_dir_mag.png"
    logging.info("Plotting stack to %s" % stackfn)
    plot_stack_stats(dir_median, dir_var, mag_median, mag_wmean, stackfn)

    geotif_outfn = stack_basename + "_masked_vel_my_median.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, mag_median, int(epsg_code), gt, nan_value=np.nan)

    geotif_outfn = stack_basename + "_masked_vel_my_wmean.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, mag_wmean, int(epsg_code), gt, nan_value=np.nan)

    geotif_outfn = stack_basename + "_masked_correlation_mean.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, correlation_mean, int(epsg_code), gt, nan_value=np.nan)

    geotif_outfn = stack_basename + "_masked_vel_my_var.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, mag_var, int(epsg_code), gt, nan_value=np.nan)

    geotif_outfn = stack_basename + "_masked_direction_median.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, dir_median, int(epsg_code), gt, nan_value=np.nan)

    geotif_outfn = stack_basename + "_masked_direction_var.tif"
    logging.info("Writing geotiff %s" % (geotif_outfn))
    save_geotiff(geotif_outfn, dir_var, int(epsg_code), gt, nan_value=np.nan)
