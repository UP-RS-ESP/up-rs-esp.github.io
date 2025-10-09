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

# from plot_hist import plot_hist
# from scipy.stats import gaussian_kde as kde

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


def plot_single_6panel_u_v_dir_vel_my(
    u,
    v,
    correlation,
    direction,
    velocity,
    velocity_average,
    dem_hillshade,
    pngfn,
    x_rectangle_start=0,
    y_rectangle_start=0,
    rectangle_width=0,
    rectangle_height=0,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 9), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(u, vmin=-0.5, vmax=0.5, cmap="PiYG")
    im0b = ax[0, 0].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="vertical")
    h.set_label("u (m/y)")
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 0].add_patch(rect)
    im1 = ax[0, 1].imshow(v, vmin=-0.5, vmax=0.5, cmap="PiYG")
    im1b = ax[0, 1].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="vertical")
    h.set_label("v (m/y)")
    ax[0, 1].get_xaxis().set_ticks([])
    ax[0, 1].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 1].add_patch(rect)
    im2 = ax[0, 2].imshow(correlation, vmin=0.8, vmax=1, cmap="magma")
    im2b = ax[0, 2].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im2, ax=ax[0, 2], orientation="vertical")
    h.set_label("correlation ")
    ax[0, 2].get_xaxis().set_ticks([])
    ax[0, 2].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 2].add_patch(rect)
    im3 = ax[1, 0].imshow(
        velocity,
        vmin=0,
        vmax=0.5,
        cmap="viridis",
    )
    im3b = ax[1, 0].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 0], orientation="vertical")
    h.set_label("velocity (m/y)")
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 0].add_patch(rect)
    im4 = ax[1, 1].imshow(
        direction,
        vmin=0,
        vmax=360,
        cmap="hsv",
    )
    im4b = ax[1, 1].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im4, ax=ax[1, 1], orientation="vertical")
    h.set_label("direction for v > 0 (degree)")
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 1].add_patch(rect)
    im5 = ax[1, 2].imshow(
        velocity_average,
        vmin=0,
        vmax=0.5,
        cmap="viridis",
    )
    im5b = ax[1, 2].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im5, ax=ax[1, 2], orientation="vertical")
    h.set_label("velocity (average) (m/y)")
    ax[1, 2].get_xaxis().set_ticks([])
    ax[1, 2].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 2].add_patch(rect)
    fig.suptitle("%s" % (pngfn))
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_single_u_v_dir_vel(
    u,
    v,
    correlation,
    direction,
    velocity,
    velocity_masked,
    dem_hillshade,
    pngfn,
    x_rectangle_start=0,
    y_rectangle_start=0,
    rectangle_width=0,
    rectangle_height=0,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=3, figsize=(16, 9), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(u, vmin=-2, vmax=2, cmap="PiYG")
    im0b = ax[0, 0].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="vertical")
    h.set_label("u (pixel)")
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 0].add_patch(rect)
    im1 = ax[0, 1].imshow(v, vmin=-2, vmax=2, cmap="PiYG")
    im1b = ax[0, 1].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="vertical")
    h.set_label("v (pixel)")
    ax[0, 1].get_xaxis().set_ticks([])
    ax[0, 1].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 1].add_patch(rect)
    im2 = ax[0, 2].imshow(correlation, vmin=0.8, vmax=1, cmap="magma")
    im2b = ax[0, 2].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im2, ax=ax[0, 2], orientation="vertical")
    h.set_label("correlation (masked)")
    ax[0, 2].get_xaxis().set_ticks([])
    ax[0, 2].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 2].add_patch(rect)
    im3 = ax[1, 0].imshow(
        velocity,
        vmin=0,
        vmax=1,
        cmap="viridis",
    )
    im3b = ax[1, 0].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 0], orientation="vertical")
    h.set_label("velocity (m/y)")
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 0].add_patch(rect)
    im4 = ax[1, 1].imshow(
        direction,
        vmin=0,
        vmax=360,
        cmap="hsv",
    )
    im4b = ax[1, 1].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im4, ax=ax[1, 1], orientation="vertical")
    h.set_label("direction (degree)")
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 1].add_patch(rect)
    im5 = ax[1, 2].imshow(
        velocity_masked,
        vmin=0,
        vmax=1,
        cmap="viridis",
    )
    im5b = ax[1, 2].imshow(dem_hillshade, cmap="gray", alpha=0.5)
    h = plt.colorbar(im5, ax=ax[1, 2], orientation="vertical")
    h.set_label("velocity (masked) (m/y)")
    ax[1, 2].get_xaxis().set_ticks([])
    ax[1, 2].get_yaxis().set_ticks([])
    rect = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[1, 2].add_patch(rect)
    fig.suptitle("%s" % (pngfn))
    fig.savefig(pngfn, dpi=300)
    plt.close()


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
            median_u = np.nanmedian(u_ar[:, i, j])
            median_v = np.nanmedian(v_ar[:, i, j])
            velocity_direction[i, j] = ArithmeticDegree_to_GeographicDegree(
                np.rad2deg(np.arctan2(median_v, median_u))
            )
            velocity_magnitude[i, j] = np.sqrt(median_u**2 + median_v**2)
            velocity_nrm[i, j] = np.count_nonzero(~np.isnan(u_ar[:, i, j]))
    return velocity_magnitude, velocity_direction, velocity_nrm


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


def load_mask(filename, mask_size):
    date1 = os.path.basename(filename).split("_")[0]
    date2 = os.path.basename(filename).split("_")[1]
    fname = os.path.join(
        "/".join(os.path.dirname(filename).split("/")[:-1]),
        "MASKS",
        "%s_%s_NDSI_NDVI_CLOUD_mask.tif" % (date1, date2),
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


def load_v_files_nomask(dirname, height, width):
    logging.info("Finding v tif files")
    v_files = glob.glob(os.path.join(dirname, "*_v.tif"))
    v_files.sort()
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading v files"):
        cfile = v_files[i]
        # oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        v_ar[i, :, :] = bm
    return v_files, deltaT, v_ar


def load_v_files(dirname, correlation_ar, height, width):
    logging.info("Finding v tif files")
    v_files = glob.glob(os.path.join(dirname, "*_v.tif"))
    v_files.sort()
    v_ar = np.empty((len(v_files), height, width), dtype=np.float32)
    v_ar.fill(np.nan)
    bm_nanmean = np.empty((len(u_files)), dtype=np.float32)
    bm_nanmean.fill(np.nan)
    for i in tqdm.tqdm(range(len(v_files)), desc="Loading v files"):
        cfile = v_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        deltaT = get_deltaT_from_filename(cfile)
        # filter bm results with correlation coefficient. Keep only points above threshold
        # correlation_nan = len(bm[correlation_ar[i, :, :] < c_threshold])
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        bm[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile, bm.shape)
        bm[ndvi_ndsi_mask] = np.nan
        bm_nanmean[i] = np.nanmean(bm)
        bm = bm - bm_nanmean[i]
        v_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return v_files, deltaT, v_ar, bm_nanmean


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


def load_u_files(dirname, correlation_ar, height, width):
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
    u_ar = np.empty((len(u_files), height, width), dtype=np.float32)
    u_ar.fill(np.nan)
    bm_nanmean = np.empty((len(u_files)), dtype=np.float32)
    bm_nanmean.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        deltaT = get_deltaT_from_filename(cfile)
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        bm[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile, bm.shape)
        bm[ndvi_ndsi_mask] = np.nan
        bm_nanmean[i] = np.nanmean(bm)
        bm = bm - bm_nanmean[i]
        u_ar[i, :, :] = bm * (satellite_resolution_m / oversampling) / deltaT
    return u_files, deltaT, u_ar, bm_nanmean


def load_u_files_rotation(dirname, correlation_ar, height, width):
    logging.info("Finding u tif files")
    u_files = glob.glob(os.path.join(dirname, "*_u.tif"))
    u_files.sort()
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
    rotate_angle_u = np.empty(len(u_files), dtype=np.float32)
    rotate_angle_u.fill(np.nan)
    for i in tqdm.tqdm(range(len(u_files)), desc="Loading u files"):
        cfile = u_files[i]
        oversampling = int(os.path.basename(cfile).split("_")[2][2:])
        matchingstep = int(os.path.basename(cfile).split("_")[5][2:])
        bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
            cfile, matchingstep=matchingstep
        )
        (
            bm_f,
            u_ar_ax0_mean[i, :],
            u_ar_ax0_mean_postcor[i, :],
            u_ar_ax1_mean[i, :],
            u_ar_ax1_mean_postcor[i, :],
            rotate_angle_u[i],
        ) = correct_striping_rotate(
            bm,
            pngfn=os.path.join(
                u_pngs_dir, os.path.basename(cfile)[:-4] + "_striping_correction.png"
            ),
        )
        deltaT = get_deltaT_from_filename(cfile)
        # deltaT = 10  # force time difference to 10 years
        # filter bm results with correlation coefficient. Keep only points above threshold
        # correlation_nan = len(bm[correlation_ar[i, :, :] < c_threshold])
        bm[correlation_ar[i, :, :] < c_threshold] = np.nan
        bm_f[correlation_ar[i, :, :] < c_threshold] = np.nan
        # filter bm results with slope. Use only slopes exceeding 5 degree
        # slope_nan = len(bm[dem_slope < slope_threshold])
        bm[dem_slope < slope_threshold] = np.nan
        bm_f[dem_slope < slope_threshold] = np.nan
        # filter with NDVI and NDSI mask
        ndvi_ndsi_mask = load_mask(cfile, bm.shape)
        # if ndvi_ndsi_mask.shape != bm.shape:
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask, ndvi_ndsi_mask[-1]))
        #     ndvi_ndsi_mask = np.vstack((ndvi_ndsi_mask.T, ndvi_ndsi_mask.T[-1])).T
        # ndvi_ndsi_nan = len(bm[ndvi_ndsi_mask == True])
        bm[ndvi_ndsi_mask] = np.nan
        bm_f[ndvi_ndsi_mask] = np.nan
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
        u_arf[i, :, :] = bm_f * (satellite_resolution_m / oversampling) / deltaT
        # u_ar[i, :, :] = bm
    return u_files, deltaT, u_ar, u_arf


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
    dirname, geotiffn, ds_gt, epsg_code, save_correlation_tif=False
):
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


def plot_single_u_v_dir_vel_average_loop(u_ar, v_ar, magnitude_average):
    for i in tqdm.tqdm(range(u_ar.shape[0]), desc="Plotting PNGs"):
        direction, magnitude = calc_direction_velocity(u_ar[i, :, :], v_ar[i, :, :])
        fname1 = os.path.basename(u_files[i]).split(".")[0][:-1]
        pngfn = fname1 + "6panel_vuvelocity_masked.png"
        x_range1 = int(u_ar[i, :, :].shape[0] / 3 - 500)
        x_range2 = int(u_ar[i, :, :].shape[0] / 3 + 500)
        y_range1 = int(u_ar[i, :, :].shape[1] / 3 - 500)
        y_range2 = int(u_ar[i, :, :].shape[1] / 3 + 500)
        plot_single_6panel_u_v_dir_vel_my(
            u_ar[i, :, :],
            v_ar[i, :, :],
            correlation_ar[i, :, :],
            direction,
            magnitude,
            magnitude_average,
            dem_hs,
            pngfn,
            x_rectangle_start=x_range1,
            y_rectangle_start=y_range1,
            rectangle_width=x_range2 - x_range1,
            rectangle_height=y_range2 - y_range1,
        )
        pngfn = fname1 + "6panel_vuvelocity_masked_zoom.png"
        plot_single_6panel_u_v_dir_vel_my(
            u_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            v_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            correlation_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            direction[x_range1:x_range2, y_range1:y_range2],
            magnitude[x_range1:x_range2, y_range1:y_range2],
            magnitude_average[x_range1:x_range2, y_range1:y_range2],
            dem_hs[x_range1:x_range2, y_range1:y_range2],
            pngfn,
        )
        # geotiff_outfn = fname1 + "mask_pixel_u.tif"
        # save_geotiff(
        #     geotiff_outfn, u_ar_nomask[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_pixel_v.tif"
        # save_geotiff(
        #     geotiff_outfn, v_ar_nomask[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_my_u.tif"
        # save_geotiff(
        #     geotiff_outfn, u_ar_masked[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_my_v.tif"
        # save_geotiff(
        #     geotiff_outfn, v_ar_masked[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "correlation.tif"
        # save_geotiff(geotiff_outfn, correlation_ar[i, :, :], epsg_code, ds_gt, nan_value=np.nan)
        # geotiff_outfn = fname1 + "velocity_magnitude_pixel.tif"
        # save_geotiff(geotiff_outfn, magnitude, epsg_code, ds_gt, nan_value=np.nan)


def plot_single_u_v_dir_vel_loop(u_ar, v_ar, u_ar_masked, v_ar_masked):
    for i in range(u_ar.shape[0]):
        direction, magnitude = calc_direction_velocity(u_ar[i, :, :], v_ar[i, :, :])
        direction_masked, magnitude_masked = calc_direction_velocity(
            u_ar_masked[i, :, :], v_ar_masked[i, :, :]
        )
        fname1 = os.path.basename(u_files[i]).split(".")[0][:-1]
        pngfn = fname1 + "6panel_vuvelocity_masked.png"
        x_range1 = int(u_ar[i, :, :].shape[0] / 3 - 500)
        x_range2 = int(u_ar[i, :, :].shape[0] / 3 + 500)
        y_range1 = int(u_ar[i, :, :].shape[1] / 3 - 500)
        y_range2 = int(u_ar[i, :, :].shape[1] / 3 + 500)
        plot_single_6panel_u_v_dir_vel_my(
            u_ar[i, :, :],
            v_ar[i, :, :],
            correlation_ar[i, :, :],
            direction,
            magnitude,
            magnitude_masked,
            dem_hs,
            pngfn,
            x_rectangle_start=x_range1,
            y_rectangle_start=y_range1,
            rectangle_width=x_range2 - x_range1,
            rectangle_height=y_range2 - y_range1,
        )
        pngfn = fname1 + "6panel_vuvelocity_masked_zoom.png"
        plot_single_6panel_u_v_dir_vel_my(
            u_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            v_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            correlation_ar[i, :, :][x_range1:x_range2, y_range1:y_range2],
            direction[x_range1:x_range2, y_range1:y_range2],
            magnitude[x_range1:x_range2, y_range1:y_range2],
            magnitude_masked[x_range1:x_range2, y_range1:y_range2],
            dem_hs[x_range1:x_range2, y_range1:y_range2],
            pngfn,
        )
        # geotiff_outfn = fname1 + "mask_pixel_u.tif"
        # save_geotiff(
        #     geotiff_outfn, u_ar_nomask[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_pixel_v.tif"
        # save_geotiff(
        #     geotiff_outfn, v_ar_nomask[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_my_u.tif"
        # save_geotiff(
        #     geotiff_outfn, u_ar_masked[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "mask_my_v.tif"
        # save_geotiff(
        #     geotiff_outfn, v_ar_masked[i, :, :], epsg_code, ds_gt, nan_value=np.nan
        # )
        # geotiff_outfn = fname1 + "correlation.tif"
        # save_geotiff(geotiff_outfn, correlation_ar[i, :, :], epsg_code, ds_gt, nan_value=np.nan)
        # geotiff_outfn = fname1 + "velocity_magnitude_pixel.tif"
        # save_geotiff(geotiff_outfn, magnitude, epsg_code, ds_gt, nan_value=np.nan)


def gaussian_filter_nan(displacement_my, sigma=2, truncate=4):
    # Gaussian Filter that ignores NaNs. First replaces NaNs with zeros and then uses a second run on a binary mask to remove the effect of 0.
    V = displacement_my.copy()
    V[np.isnan(displacement_my)] = 0
    VV = gaussian_filter(V, sigma=sigma, truncate=truncate, mode="nearest")
    W = 0 * displacement_my.copy() + 1
    W[np.isnan(displacement_my)] = 0
    WW = gaussian_filter(W, sigma=sigma, truncate=truncate, mode="nearest")
    return VV / WW


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


def correct_striping_rotate(bm, pngfn, plot_figure=True):
    # find dimension of new (correct_striping_rotateated) array and find starting/ending row indices
    row_data_length = np.zeros(bm.shape[1], dtype=np.int64)
    row_data_startend = np.empty((bm.shape[1], 2), dtype=np.int64)
    row_data_startend.fill(-1)
    for i in range(bm.shape[1]):
        if np.all(np.isnan(bm[:, i])):
            continue
        (row_data_idx,) = np.where(~np.isnan(bm[:, i]))
        row_data_startend[i] = np.array([np.min(row_data_idx), np.max(row_data_idx)])
        row_data_length[i] = len(row_data_idx)
    i_start = 3000
    i_end = 12000  # len(np.argwhere(row_data_startend[:,0] > -1))
    y = row_data_startend[i_start:i_end, 0]
    x = np.arange(0, len(y), 1)
    M = x[:, np.newaxis] ** [0, 1]
    p, res, rnk, s = scipy.linalg.lstsq(M, y)
    rotate_angle = np.rad2deg(np.arctan(p[1]))
    # rotate using scipy.ndimage.rotate
    bm_r = scipy.ndimage.rotate(bm, rotate_angle, order=1, reshape=False, cval=np.nan)
    # # remove nan padding
    # bm_r_isnan = np.isnan(bm_r)
    # idx0_to_remove = []
    # for i in range(bm_r_isnan.shape[0]):
    #     if np.all(bm_r_isnan[i, :]):
    #         idx0_to_remove.append(i)
    # idx1_to_remove = []
    # for i in range(bm_r_isnan.shape[1]):
    #     if np.all(bm_r_isnan[:, i]):
    #         idx1_to_remove.append(i)
    # bm_r_nonan = np.delete(bm_r, idx0_to_remove, axis=0)
    # bm_r_nonan = np.delete(bm_r_nonan, idx1_to_remove, axis=1)
    # bm_median = np.nanmedian(bm_r_nonan, axis=0)
    # bm_median_ar = np.repeat(bm_median, bm_r_nonan.shape[0]).reshape( (bm_r_nonan.shape[1], bm_r_nonan.shape[0]) ).T
    # bm_r_nonan = bm_r_nonan - bm_median_ar
    # bm_median_postcorrection = np.nanmedian(bm_r_nonan, axis=0)
    bm_mean_ax0 = np.nanmean(bm_r, axis=0)
    bm_mean_ax0_ar = (
        np.repeat(bm_mean_ax0, bm_r.shape[0]).reshape((bm_r.shape[1], bm_r.shape[0])).T
    )
    bm_r = bm_r - bm_mean_ax0_ar
    bm_mean_ax0_postcorrection = np.nanmean(bm_r, axis=0)
    bm_mean_ax1 = np.nanmean(bm_r, axis=1)
    bm_mean_ax1_ar = (
        np.repeat(bm_mean_ax1, bm_r.shape[1]).reshape((bm_r.shape[1], bm_r.shape[0])).T
    )
    bm_r = bm_r - bm_mean_ax1_ar
    bm_mean_ax1_postcorrection = np.nanmean(bm_r, axis=1)
    bm_f = scipy.ndimage.rotate(
        bm_r, -rotate_angle, order=1, reshape=False, cval=np.nan
    )
    bm_f2 = bm - np.nanmean(bm)
    bm_mean_fullscenecorrection = np.nanmean(bm_f2, axis=0)
    if plot_figure:
        ax = plt.figure(figsize=(16, 9), dpi=300, layout="constrained").subplot_mosaic(
            """
        ABCE
        DDDE
        """
        )
        im0 = ax["A"].imshow(bm[::10, ::10], vmin=-2, vmax=2, cmap="seismic")
        ax["A"].get_xaxis().set_ticks([])
        ax["A"].get_yaxis().set_ticks([])
        ax["A"].set_title("Original Offset before filtering")
        im1 = ax["B"].imshow(bm_r[::10, ::10], vmin=-2, vmax=2, cmap="seismic")
        ax["B"].get_xaxis().set_ticks([])
        ax["B"].get_yaxis().set_ticks([])
        ax["B"].set_title("Rotated Offset after mean column filtering")
        im1 = ax["C"].imshow(bm_f[::10, ::10], vmin=-2, vmax=2, cmap="seismic")
        ax["C"].get_xaxis().set_ticks([])
        ax["C"].get_yaxis().set_ticks([])
        ax["C"].set_title("Offset after filtering for each column")
        plt.colorbar(im0, ax=[ax["A"], ax["B"], ax["C"]], location="bottom")
        ax["D"].plot(bm_mean_ax0, "k-", lw=0.5, label="mean before correction")
        ax["D"].plot(
            bm_mean_ax0_postcorrection,
            "-",
            color="darkred",
            lw=1,
            label="mean after correction",
        )
        ax["D"].plot(
            bm_mean_fullscenecorrection,
            "-",
            color="steelblue",
            lw=0.1,
            label="mean of full scene correction",
        )
        ax["D"].grid()
        ax["D"].legend()
        ax["D"].set_xlabel(
            "Range (x) distance across Landsat scene (pixel)", fontsize=16
        )
        ax["D"].set_ylabel("Mean offset (pixel)", fontsize=16)
        ax["D"].set_ylim([-2, 2])
        ax["E"].plot(
            bm_mean_ax1,
            np.arange(len(bm_mean_ax1)),
            "k-",
            lw=0.5,
            label="mean before correction",
        )
        ax["E"].plot(
            bm_mean_ax1_postcorrection,
            np.arange(len(bm_mean_ax1_postcorrection)),
            "-",
            color="darkred",
            lw=1,
            label="mean after correction",
        )
        ax["E"].plot(
            bm_mean_fullscenecorrection,
            np.arange(len(bm_mean_fullscenecorrection)),
            "-",
            color="steelblue",
            lw=0.1,
            label="mean of full scene correction",
        )
        ax["E"].grid()
        ax["E"].legend()
        ax["E"].set_ylabel(
            "Azimuth (y) distance along Landsat scene (pixel)", fontsize=16
        )
        ax["E"].set_xlabel("Mean offset (pixel)", fontsize=16)
        ax["E"].set_xlim([-2, 2])
        plt.suptitle("%s" % (os.path.basename(pngfn)[:-4]), fontsize=21)
        plt.savefig(pngfn, dpi=300)
        plt.close()
    return (
        bm_f,
        bm_mean_ax0,
        bm_mean_ax0_postcorrection,
        bm_mean_ax1,
        bm_mean_ax1_postcorrection,
        rotate_angle,
    )


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dirname = sys.argv[1]
    dirname_os01 = sys.argv[2]
    geotiffn = sys.argv[3]
    dem_fname = sys.argv[4]
    plot_pngs = False
    calc_mode = False
    # python run_stack_block_matching_fulldirectory.py  \
    # CORR_os05_bs61_sr06_ms05/ \
    # CORR_os01_bs11_sr03_ms01/ \
    # CORR_os05_bs61_sr06_ms05_ \
    # COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif
    # dirname = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs61_sr06_ms05/"
    # dirname_os01 = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os01_bs11_sr03_ms01/"
    # geotiffn = "/raid2-gpu2/bodo/LANDSAT/P231R077/CORR_os05_bs61_sr06_ms05_"
    # dem_fname = (
    #     "/raid2-gpu2/bodo/LANDSAT/P231R077/COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    # )

    # fname = "20000808_20230731_os05_bs91_sr06_ms05_u.tif"
    # dem_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    # matchingstep = 5
    # bm, foo_ds_gt, foo_ds_proj, epsg = load_blockmatching_tif(
    #     fname, matchingstep=matchingstep
    # )

    satellite_resolution_m = 15
    c_threshold = 0.8
    slope_threshold = 5
    deltadirection_threshold = 45
    gaussian_sigma = 2
    gaussian_truncate = 4

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )

    height, width, ds_gt, epsg_code = get_file_dimensions(dirname_os01)
    correlation_ar = load_correlation_files(
        dirname, geotiffn, ds_gt, epsg_code, save_correlation_tif=True
    )
    # u_files, deltaT, u_ar_nomask = load_u_files_nomask(dirname, height, width)
    # v_files, deltaT, v_ar_nomask = load_v_files_nomask(dirname, height, width)
    u_files, deltaT, u_ar, u_nanmean = load_u_files(
        dirname, correlation_ar, height, width
    )
    v_files, deltaT, v_ar, v_nanmean = load_v_files(
        dirname, correlation_ar, height, width
    )

    logging.info(
        "Calculating median velocity and direction for each date before masking"
    )
    velocity_magnitude, velocity_direction, velocity_nrm = (
        calc_median_magnitude_direction(u_ar, v_ar)
    )
    geotiff_outfn = (
        geotiffn + "median_velocity_magnitude_pixel_correlation08_noaspectmask.tif"
    )
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_magnitude, epsg_code, ds_gt, nan_value=np.nan)
    geotiff_outfn = (
        geotiffn + "median_velocity_direction_correlation08_noaspectmask.tif"
    )
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_direction, epsg_code, ds_gt, nan_value=np.nan)
    geotiff_outfn = geotiffn + "nre_velocity_correlation08_noaspectmask.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff_8bit(geotiff_outfn, velocity_nrm, epsg_code, ds_gt, nan_value=255)

    logging.info("Applying gaussian smoothing on u_ar with sigma=%d" % gaussian_sigma)
    for i in tqdm.tqdm(range(len(u_ar)), desc="Gaussian filt u_ar"):
        u_ar_gf = np.empty_like(u_ar)
        u_ar_gf.fill(np.nan)
        u_ar_gf[i, :, :] = gaussian_filter_nan(
            u_ar[i, :, :], sigma=gaussian_sigma, truncate=gaussian_truncate
        )

    logging.info("Applying gaussian smoothing on v_ar with sigma=%d" % gaussian_sigma)
    for i in tqdm.tqdm(range(len(v_ar)), desc="Gaussian filt v_ar"):
        v_ar_gf = np.empty_like(v_ar)
        v_ar_gf.fill(np.nan)
        v_ar_gf[i, :, :] = gaussian_filter_nan(
            v_ar[i, :, :], sigma=gaussian_sigma, truncate=gaussian_truncate
        )

    logging.info("Calculating velocity and direction for each multistep and resolution")
    direction, magnitude = calc_multistep_direction_velocity(u_ar, v_ar)
    logging.info("Calculating aspect and direction angle difference")
    deltadirection = calc_dem_aspect_direction_difference(dem_aspect, direction)
    logging.info(
        "Mask out pixels with an angle difference above %d degree"
        % deltadirection_threshold
    )
    u_ar_masked, v_ar_masked = mask_dem_aspect_direction(
        deltadirection, u_ar, v_ar, deltadirection_threshold=deltadirection_threshold
    )
    logging.info(
        "Calculating median velocity and direction for each date after masking"
    )
    velocity_magnitude, velocity_direction, velocity_nrm = (
        calc_median_magnitude_direction(u_ar, v_ar)
    )
    geotiff_outfn = geotiffn + "median_velocity_magnitude_my.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_magnitude, epsg_code, ds_gt, nan_value=np.nan)
    geotiff_outfn = geotiffn + "median_velocity_direction.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, velocity_direction, epsg_code, ds_gt, nan_value=np.nan)
    geotiff_outfn = geotiffn + "nre_velocity.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff_8bit(geotiff_outfn, velocity_nrm, epsg_code, ds_gt, nan_value=255)

    if plot_pngs == True:
        plot_single_u_v_dir_vel_average_loop(
            u_ar, v_ar, magnitude_average=velocity_magnitude
        )
    if calc_mode == True:
        logging.info(
            "Calculating mode velocity and direction for each date after masking"
        )
        velocity_magnitude, velocity_direction = calc_mode_magnitude_direction(
            u_ar, v_ar
        )
        geotiff_outfn = geotiffn + "mode_velocity_magnitude_my.tif"
        logging.info("Writing geotiff %s" % (geotiff_outfn))
        save_geotiff(
            geotiff_outfn, velocity_magnitude, epsg_code, ds_gt, nan_value=np.nan
        )
        geotiff_outfn = geotiffn + "mode_velocity_direction.tif"
        logging.info("Writing geotiff %s" % (geotiff_outfn))
        save_geotiff(
            geotiff_outfn, velocity_direction, epsg_code, ds_gt, nan_value=np.nan
        )

    # now could add median velocity filtered with direction variance
    logging.info("Calculating direction variance after masking")
    direction_variance = calc_direction_variance(u_ar, v_ar)
    geotiff_outfn = geotiffn + "variance_direction.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, direction_variance, epsg_code, ds_gt, nan_value=np.nan)
    logging.info("Calculating magnitude variance after masking")
    magnitude_variance = calc_magnitude_variance(u_ar, v_ar)
    geotiff_outfn = geotiffn + "variance_magnitude_my.tif"
    logging.info("Writing geotiff %s" % (geotiff_outfn))
    save_geotiff(geotiff_outfn, magnitude_variance, epsg_code, ds_gt, nan_value=np.nan)
