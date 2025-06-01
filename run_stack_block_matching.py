import numpy as np
import numba as nb
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt


gdal.UseExceptions()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def load_blockmatching_tif(fname):
    blockmatching_ds = gdal.Open(fname)
    blockmatching_ds_gt = blockmatching_ds.GetGeoTransform()
    blockmatching_ds_proj = blockmatching_ds.GetProjection()
    blockmatching_B1 = np.array(blockmatching_ds.GetRasterBand(1).ReadAsArray()).astype(
        "float32"
    )
    blockmatching_ds = None
    return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj


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


def get_deltaT_from_filename(u_files):
    deltaT_y = np.empty(len(u_files), dtype=np.float32)
    deltaT_y.fill(np.nan)
    for i in range(len(u_files)):
        date1 = pd.to_datetime(os.path.basename(u_files[i]).split("_")[0])
        date2 = pd.to_datetime(os.path.basename(u_files[i]).split("_")[1])

        difference_in_years = relativedelta(date2, date1).years
        difference_in_days = relativedelta(date2, date1).days / 365.25
        difference_in_years += difference_in_days
        deltaT_y[i] = difference_in_years
    return deltaT_y.astype(np.float32)


if __name__ == "__main__":

    dirname = sys.argv[1]
    stepsize = int(sys.argv[2])
    geotiffn = sys.argv[3]

    # dirname = "/raid2-gpu2/bodo/LANDSAT/P232R077/BLOCKMATCHING_os01_bs31_sr03/"
    # stepsize = 15
    # geotiffn = "/raid2-gpu2/bodo/LANDSAT/P232R077/CROP/LC08_L1TP_232077_20141102_20200910_02_T1_B8.TIF"

    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
    logging.info("Loading first u tif file to get array dimensions")
    foo_ds, foo_ds_gt, foo_ds_proj = load_blockmatching_tif(u_files[0])
    height = foo_ds.shape[0]
    width = foo_ds.shape[1]
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u tif files"):
        foo_ds, foo_ds_gt, foo_ds_proj = load_blockmatching_tif(u_files[i])
        u_ar[i, :, :] = foo_ds

    logging.info("Finding v tif files")
    v_files = glob.glob(os.path.join(dirname, "*_v.tif"))
    v_files.sort()
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading v tif files"):
        foo_ds, foo_ds_gt, foo_ds_proj = load_blockmatching_tif(v_files[i])
        v_ar[i, :, :] = foo_ds

    logging.info("Finding correlation coefficient tif files")
    correlation_files = glob.glob(os.path.join(dirname, "*_correlation.tif"))
    correlation_files.sort()
    correlation_ar = np.empty((len(correlation_files), height, width), dtype=np.float32)
    correlation_ar.fill(np.nan)
    for i in tqdm.tqdm(
        range(len(correlation_files)), desc="Loading correlation tif files"
    ):
        foo_ds, foo_ds_gt, foo_ds_proj = load_blockmatching_tif(correlation_files[i])
        correlation_ar[i, :, :] = foo_ds

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
