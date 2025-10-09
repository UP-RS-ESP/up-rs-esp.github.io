from datetime import date
import numpy as np
import numba as nb
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage import measure
from skimage import filters
from skimage import data, util
from skimage import morphology
from skimage import feature
from skimage import segmentation
from plot_hist import plot_hist
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import binary_erosion
from scipy.ndimage import gaussian_filter
from shapely import Polygon
from shapely import geometry

# from plot_hist import plot_hist
# from scipy.stats import gaussian_kde as kde

gdal.UseExceptions()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def load_dem_aspect_slope_files(dem_fname):
    logging.info("Loading DEM file %s" % dem_fname)
    dem, dem_gt, dem_proj, dem_epsg = load_dem_tif(dem_fname)
    # dem_slope, dem_aspect = np_slope_aspect(dem, dem_gt[1])
    # !gdaldem aspect COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_aspect.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    # !gdaldem slope COP15_DEM_NW_ARGENTINA_UTM20.tif COP15_DEM_NW_ARGENTINA_UTM20_slope.tif -co COMPRESS=DEFLATE -co ZLEVEL=7
    #!gdaldem hillshade COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif COP15_DEM_NW_ARGENTINA_UTM20_P231R077_hs.tif -co COMPRESS=DEFLATE -co ZLEVEL=9
    dem_dir = os.path.dirname(dem_fname)
    aspect_fname_lst = glob.glob(
        os.path.join(dem_dir, os.path.basename(dem_fname)[0:37] + "_aspect.tif")
    )
    aspect_fname = aspect_fname_lst[0]
    logging.info("Loading DEM-aspect file %s" % aspect_fname)
    dem_aspect, aspect_gt, aspect_proj, aspect_epsg = load_dem_tif(aspect_fname)
    dem_aspect[dem_aspect < 0] = np.nan
    slope_fname_lst = glob.glob(
        os.path.join(dem_dir, os.path.basename(dem_fname)[0:37] + "_aspect.tif")
    )
    slope_fname = slope_fname_lst[0]
    logging.info("Loading DEM-slope file %s" % slope_fname)
    dem_slope, slope_gt, slope_proj, slope_epsg = load_dem_tif(slope_fname)
    dem_slope[dem_slope < 0] = np.nan
    hs_fname_lst = glob.glob(
        os.path.join(dem_dir, os.path.basename(dem_fname)[0:37] + "_hs.tif")
    )
    hs_fname = hs_fname_lst[0]
    logging.info("Loading DEM-hillshade file %s" % hs_fname)
    dem_hs, hs_gt, hs_proj, hs_epsg = load_Landsat_tif8bit(hs_fname)
    dem_hs = np.ma.masked_where(np.isnan(dem_slope), dem_hs)
    return dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs


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
    return blockmatching_B1, blockmatching_ds_gt, blockmatching_ds_proj, epsg


def load_Landsat_tif8bit(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray())
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def load_dem_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
    Landsat_B8[Landsat_B8 == -9999] = np.nan
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, epsg


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1))
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == -9999] = np.nan
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


def plot_3panel_overview(
    dem,
    dem_hs,
    displacement_my,
    nre,
    pngfn,
):
    fig, ax = plt.subplots(
        nrows=3, ncols=1, figsize=(8, 10), dpi=300, layout="constrained"
    )
    im0 = ax[0].imshow(
        dem,
        vmin=np.nanpercentile(dem, 2),
        vmax=np.nanpercentile(dem, 98),
        cmap="terrain",
    )
    im0b = ax[0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0], orientation="horizontal", shrink=0.8)
    h.set_label("elevation (m)", fontsize=12)
    ax[0].get_xaxis().set_ticks([])
    ax[0].get_yaxis().set_ticks([])
    im2 = ax[1].imshow(
        displacement_my,
        cmap="plasma",
        vmin=0,
        vmax=0.2,
    )
    im2b = ax[1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im2, ax=ax[1], orientation="horizontal", shrink=0.8)
    h.set_label("velocity (m/y)", fontsize=12)
    ax[1].get_xaxis().set_ticks([])
    ax[1].get_yaxis().set_ticks([])
    im3 = ax[2].imshow(
        nre,
        vmin=1,
        vmax=np.nanpercentile(nre, 98),
        cmap="magma",
    )
    im3b = ax[2].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[2], orientation="horizontal", shrink=0.8)
    h.set_label("number of measurements", fontsize=12)
    ax[2].get_xaxis().set_ticks([])
    ax[2].get_yaxis().set_ticks([])
    fig.suptitle("%s" % (pngfn))
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_4panel_overview(
    dem,
    dem_hs,
    dem_slope,
    displacement_my,
    displacement_variance_my,
    pngfn,
    x_rectangle_start=0,
    y_rectangle1_start=0,
    y_rectangle2_start=0,
    y_rectangle3_start=0,
    rectangle_width=0,
    rectangle_height=0,
):
    fig, ax = plt.subplots(
        nrows=2, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    im0 = ax[0, 0].imshow(
        dem,
        vmin=np.nanpercentile(dem, 2),
        vmax=np.nanpercentile(dem, 98),
        cmap="terrain",
    )
    im0b = ax[0, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal", shrink=0.8)
    h.set_label("elevation (m)")
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    rect1 = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle1_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 0].add_patch(rect1)
    rect2 = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle2_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 0].add_patch(rect2)
    rect3 = matplotlib.patches.Rectangle(
        (x_rectangle_start, y_rectangle3_start),
        rectangle_width,
        rectangle_height,
        linewidth=1,
        edgecolor="k",
        facecolor="none",
    )
    ax[0, 0].add_patch(rect3)
    im1 = ax[0, 1].imshow(
        dem_slope, cmap="viridis", norm=matplotlib.colors.LogNorm(vmin=0.1, vmax=50)
    )
    im1b = ax[0, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="horizontal", shrink=0.8)
    h.set_label("log slope (degree)")
    # ax[0, 1].get_xaxis().set_ticks([])
    # ax[0, 1].get_yaxis().set_ticks([])
    im2 = ax[1, 0].imshow(
        displacement_my,
        cmap="plasma",
        vmin=0,
        vmax=0.2,
    )
    im2b = ax[1, 0].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im2, ax=ax[1, 0], orientation="horizontal", shrink=0.8)
    h.set_label("velocity (m/y)")
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    im3 = ax[1, 1].imshow(
        displacement_variance_my,
        vmin=0,
        vmax=0.1,
        cmap="magma",
    )
    im3b = ax[1, 1].imshow(dem_hs, cmap="gray", alpha=0.5)
    h = plt.colorbar(im3, ax=ax[1, 1], orientation="horizontal", shrink=0.8)
    h.set_label("velocity variance (m/y)")
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    fig.suptitle("%s" % (pngfn))
    fig.savefig(pngfn, dpi=300)
    plt.close()


def movingaverage(x, window_size):
    window = np.ones(int(window_size)) / float(window_size)
    return np.convolve(x, window, "same")


def plot_profiles(
    WE_distance_km,
    dem_clip1,
    dem_slope_clip1,
    displacement_my_clip1,
    dem_clip2,
    dem_slope_clip2,
    displacement_my_clip2,
    dem_clip3,
    dem_slope_clip3,
    displacement_my_clip3,
):
    profile_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_profile.png"
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    ax[0].plot(WE_distance_km, np.nanmean(dem_clip1, axis=0), "k-", label="Elevation")
    # ax[0].set_xlabel('W-E Distance (km)')
    ax[0].set_ylabel("Elevation (m)", fontsize=16)
    ax[0].grid()
    ax0b = ax[0].twinx()
    ax0b.plot(
        WE_distance_km,
        np.nanmean(dem_slope_clip1, axis=0),
        "-",
        linewidth=1,
        color="navy",
        label="Slope",
    )
    ax0b.set_ylabel("Slope (degree)", color="navy")
    ax0b.set_ylim([0, 30])
    ax[1].plot(
        WE_distance_km,
        np.nanmean(displacement_my_clip1, axis=0),
        ",",
        linewidth=0.1,
        color="gray",
        label="Displacement",
    )
    ax[1].plot(
        WE_distance_km,
        movingaverage(np.nanmean(displacement_my_clip1, axis=0), 100),
        "-",
        linewidth=2,
        color="firebrick",
        label="Displacement",
    )
    ax[1].set_xlabel("W-E Distance (km)", fontsize=16)
    ax[1].set_ylabel("Displacement Magnitude (m/y)", fontsize=16)
    ax[1].grid()
    ax[1].set_ylim([0, 1])
    fig.suptitle("%s" % (profile_pngfn))
    fig.savefig(profile_pngfn, dpi=300)
    plt.close()
    profile_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_3profiles.png"
    fig, ax = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    ax[0].plot(WE_distance_km, np.nanmean(dem_clip1, axis=0), "k-", label="Elevation")
    # ax[0].set_ylabel('Elevation (m)', fontsize=16)
    ax[0].grid()
    ax0b = ax[0].twinx()
    ax0b.plot(
        WE_distance_km,
        np.nanmean(displacement_my_clip1, axis=0),
        ",",
        linewidth=0.1,
        color="gray",
        label="Displacement",
    )
    ax0b.plot(
        WE_distance_km,
        movingaverage(np.nanmean(displacement_my_clip1, axis=0), 100),
        "-",
        linewidth=2,
        color="firebrick",
        label="Displacement",
    )
    # ax0b.set_ylabel('Displacement Magnitude (m/y)', fontsize=16, color='firebrick')
    ax0b.set_ylim([0, 1])
    ax[1].plot(WE_distance_km, np.nanmean(dem_clip2, axis=0), "k-", label="Elevation")
    ax[1].set_ylabel("Elevation (m)", fontsize=16)
    ax[1].grid()
    ax1b = ax[1].twinx()
    ax1b.plot(
        WE_distance_km,
        np.nanmean(displacement_my_clip2, axis=0),
        ",",
        linewidth=0.1,
        color="gray",
        label="Displacement",
    )
    ax1b.plot(
        WE_distance_km,
        movingaverage(np.nanmean(displacement_my_clip2, axis=0), 100),
        "-",
        linewidth=2,
        color="firebrick",
        label="Displacement",
    )
    ax1b.set_ylabel("Displacement Magnitude (m/y)", fontsize=16, color="firebrick")
    ax1b.set_ylim([0, 1])
    ax[2].plot(WE_distance_km, np.nanmean(dem_clip3, axis=0), "k-", label="Elevation")
    # ax[2].set_ylabel('Elevation (m)', fontsize=16)
    ax[2].grid()
    ax2b = ax[2].twinx()
    ax2b.plot(
        WE_distance_km,
        np.nanmean(displacement_my_clip3, axis=0),
        ",",
        linewidth=0.1,
        color="gray",
        label="Displacement",
    )
    ax2b.plot(
        WE_distance_km,
        movingaverage(np.nanmean(displacement_my_clip3, axis=0), 100),
        "-",
        linewidth=2,
        color="firebrick",
        label="Displacement",
    )
    # ax2b.set_ylabel('Displacement Magnitude (m/y)', fontsize=16, color='firebrick')
    ax2b.set_ylim([0, 1])
    fig.suptitle("%s" % (profile_pngfn))
    fig.savefig(profile_pngfn, dpi=300)
    plt.close()


def plot_3profiles_overview():
    pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_overview.png"
    skipstep = 10
    y_rectangle1_start = 3000
    y_rectangle1_end = 3500
    y_rectangle2_start = 6000
    y_rectangle2_end = 6500
    y_rectangle3_start = 10000
    y_rectangle3_end = 10500
    x_rectangle_start = 0
    x_rectangle_end = dem.shape[1]
    plot_4panel_overview(
        dem[::skipstep, ::skipstep],
        dem_hs[::skipstep, ::skipstep],
        dem_slope[::skipstep, ::skipstep],
        displacement_my[::skipstep, ::skipstep],
        displacement_variance_my[::skipstep, ::skipstep],
        pngfn,
        x_rectangle_start=x_rectangle_start / skipstep,
        y_rectangle1_start=y_rectangle1_start / skipstep,
        y_rectangle2_start=y_rectangle2_start / skipstep,
        y_rectangle3_start=y_rectangle3_start / skipstep,
        rectangle_width=(x_rectangle_end / skipstep) - (x_rectangle_start / skipstep),
        rectangle_height=(y_rectangle1_end / skipstep)
        - (y_rectangle1_start / skipstep),
    )


def plot_3profiles_values():
    y_rectangle1_start = 3000
    y_rectangle1_end = 3500
    y_rectangle2_start = 6000
    y_rectangle2_end = 6500
    y_rectangle3_start = 10000
    y_rectangle3_end = 10500
    x_rectangle_start = 0
    x_rectangle_end = dem.shape[1]
    x_rectangle_end = dem.shape[1]
    WE_distance_km = np.arange(0, x_rectangle_end, 1) * 15 / 1e3
    dem_clip1 = dem[
        int(y_rectangle1_start) : int(y_rectangle1_end),
        int(x_rectangle_start) : int(x_rectangle_end),
    ]
    dem_slope_clip1 = dem_slope[
        y_rectangle1_start:y_rectangle1_end, x_rectangle_start:x_rectangle_end
    ]
    dem_aspect_clip1 = dem_aspect[
        y_rectangle1_start:y_rectangle1_end, x_rectangle_start:x_rectangle_end
    ]
    dem_hs_clip1 = dem_hs[
        y_rectangle1_start:y_rectangle1_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_my_clip1 = displacement_my[
        y_rectangle1_start:y_rectangle1_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_variance_my_clip1 = displacement_variance_my[
        y_rectangle1_start:y_rectangle1_end, x_rectangle_start:x_rectangle_end
    ]
    dem_clip2 = dem[
        int(y_rectangle2_start) : int(y_rectangle2_end),
        int(x_rectangle_start) : int(x_rectangle_end),
    ]
    dem_slope_clip2 = dem_slope[
        y_rectangle2_start:y_rectangle2_end, x_rectangle_start:x_rectangle_end
    ]
    dem_aspect_clip2 = dem_aspect[
        y_rectangle2_start:y_rectangle2_end, x_rectangle_start:x_rectangle_end
    ]
    dem_hs_clip2 = dem_hs[
        y_rectangle2_start:y_rectangle2_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_my_clip2 = displacement_my[
        y_rectangle2_start:y_rectangle2_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_variance_my_clip2 = displacement_variance_my[
        y_rectangle2_start:y_rectangle2_end, x_rectangle_start:x_rectangle_end
    ]
    dem_clip3 = dem[
        int(y_rectangle3_start) : int(y_rectangle3_end),
        int(x_rectangle_start) : int(x_rectangle_end),
    ]
    dem_slope_clip3 = dem_slope[
        y_rectangle3_start:y_rectangle3_end, x_rectangle_start:x_rectangle_end
    ]
    dem_aspect_clip3 = dem_aspect[
        y_rectangle3_start:y_rectangle3_end, x_rectangle_start:x_rectangle_end
    ]
    dem_hs_clip3 = dem_hs[
        y_rectangle3_start:y_rectangle3_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_my_clip3 = displacement_my[
        y_rectangle3_start:y_rectangle3_end, x_rectangle_start:x_rectangle_end
    ]
    displacement_variance_my_clip3 = displacement_variance_my[
        y_rectangle3_start:y_rectangle3_end, x_rectangle_start:x_rectangle_end
    ]
    plot_profiles(
        WE_distance_km,
        dem_clip1,
        dem_slope_clip1,
        displacement_my_clip1,
        dem_clip2,
        dem_slope_clip2,
        displacement_my_clip2,
        dem_clip3,
        dem_slope_clip3,
        displacement_my_clip3,
    )


def plot_histogram():
    # gt starts on the western end (upper left corner)
    displacement_utm19_easting = np.arange(
        displacement_ds_gt[0],
        displacement_ds_gt[0] + (displacement_ds_gt[1] * dem.shape[1]),
        displacement_ds_gt[1],
    )
    # plot histgram
    #
    hist_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_histogram.png"
    startx = 0
    endx = dem_aspect.shape[1]
    caspect = dem_aspect[:, startx:endx].ravel()
    cdem = dem[:, startx:endx].ravel()
    cslope = dem_slope[:, startx:endx].ravel()
    cdisplacement = displacement_my[:, startx:endx].ravel()
    cdisplacement_variance = displacement_my[:, startx:endx].ravel()
    (cdisplacement_values,) = np.where(~np.isnan(cdisplacement))
    cdisplacement = cdisplacement[cdisplacement_values]
    caspect = caspect[cdisplacement_values]
    cdem = cdem[cdisplacement_values]
    cslope = cslope[cdisplacement_values]
    (cdisplacement_0,) = np.where(cdisplacement > 1e-1)
    cdisplacement = cdisplacement[cdisplacement_0]
    caspect = caspect[cdisplacement_0]
    cdem = cdem[cdisplacement_0]
    cslope = cslope[cdisplacement_0]
    (efacing_idx,) = np.where((caspect > 0) & (caspect <= 180))
    (wfacing_idx,) = np.where((caspect > 180) & (caspect <= 360))
    # Elevation clips
    dem1000_idx = np.where((cdem > 0) & (cdem <= 1000))
    dem2000_idx = np.where((cdem > 1000) & (cdem <= 2000))
    dem3000_idx = np.where((cdem > 2000) & (cdem <= 3000))
    dem4000_idx = np.where((cdem > 3000) & (cdem <= 4000))
    dem5000_idx = np.where((cdem > 4000) & (cdem <= 5000))
    dem5000a_idx = np.where((cdem > 5000))
    dem0_2km_idx = np.where((cdem > 0) & (cdem <= 2500))
    dem2_5km_idx = np.where((cdem > 2500) & (cdem <= 5000))
    dem5km_idx = np.where((cdem > 5000))
    # Eastern Cordillera clips
    (ecordillera,) = np.where(displacement_utm19_easting > 740e3)
    cdisplacement_ec = displacement_my[:, ecordillera].ravel()
    caspect_ec = dem_aspect[:, ecordillera].ravel()
    cdem_ec = dem[:, ecordillera].ravel()
    (cdisplacement_ec_values,) = np.where(~np.isnan(cdisplacement_ec))
    cdisplacement_ec = cdisplacement_ec[cdisplacement_ec_values]
    caspect_ec = caspect_ec[cdisplacement_ec_values]
    cdem_ec = cdem_ec[cdisplacement_ec_values]
    (cdisplacement_ec_0,) = np.where(cdisplacement_ec > 1e-1)
    cdisplacement_ec = cdisplacement_ec[cdisplacement_ec_0]
    cdem_ec = cdem_ec[cdisplacement_ec_0]
    caspect_ec = caspect_ec[cdisplacement_ec_0]
    (efacing_ec_idx,) = np.where((caspect_ec > 0) & (caspect_ec <= 180))
    (wfacing_ec_idx,) = np.where((caspect_ec > 180) & (caspect_ec <= 360))
    demlt5km_ec_idx = np.where((cdem_ec <= 5000))
    demgt5km_ec_idx = np.where((cdem_ec > 5000))
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    plot_hist(
        cdisplacement,
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[0],
        marker=None,
        lw=1,
        color="gray",
        label="Full area",
    )
    plot_hist(
        cdisplacement[dem0_2km_idx],
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[0],
        marker=None,
        lw=2,
        color="k",
        label="<2.5 km elevation",
    )
    plot_hist(
        cdisplacement[dem2_5km_idx],
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[0],
        marker="x",
        lw=2,
        color="navy",
        label="2.5 - 5 km elevation",
    )
    plot_hist(
        cdisplacement[dem5km_idx],
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[0],
        marker="o",
        lw=2,
        color="firebrick",
        label=">5 km elevation",
    )
    ax[0].set_yscale("log")
    ax[0].grid()
    # ax[0].set_xlabel('Downslope velocity (m/yr)')
    ax[0].set_ylabel("Frequency")
    ax[0].legend()
    # plot_hist(cdisplacement[wfacing_idx], bins=10, log_bins=False, density=True, ax=ax[1], marker=None, lw = 0.5, color='firebrick',
    #       label='West facing')
    # plot_hist(cdisplacement[efacing_idx], bins=10, log_bins=False, density=True, ax=ax[1], marker=None, lw = 0.5, color='lightblue',
    #       label='East facing')
    plot_hist(
        cdisplacement_ec[demlt5km_ec_idx],
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[1],
        marker="o",
        lw=2,
        color="firebrick",
        label="Eastern Cordillera < 5 km",
    )
    plot_hist(
        cdisplacement_ec[demgt5km_ec_idx],
        bins=10,
        log_bins=False,
        density=True,
        ax=ax[1],
        marker="s",
        lw=2,
        color="lightblue",
        label="Eastern Cordillera > 5 km",
    )
    ax[1].set_yscale("log")
    ax[1].grid()
    ax[1].set_xlabel("Downslope velocity (m/yr)", fontsize=16)
    ax[1].set_ylabel("Frequency", fontsize=16)
    ax[1].legend()
    fig.suptitle("Histogram of Displacement Velocities", fontsize=21)
    fig.savefig(hist_pngfn, dpi=300)
    plt.close()


def plot_CC_profiles():
    ccprofile_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_CC1e4m4_E_to_W.png"
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    im0 = ax[0].scatter(
        displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            >= displacement_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            >= displacement_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            >= displacement_stats_df["centroid_y"].median()
        ].v_mean,
        s=2,  # displacement_stats_df.loc[displacement_stats_df['centroid_y'] >= displacement_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[0].grid()
    ax[0].set_ylabel("Elevation (m)", fontsize=16)
    h0 = plt.colorbar(im0, ax=ax[0], orientation="horizontal", shrink=0.8)
    h0.set_label("Northern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    im1 = ax[1].scatter(
        displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            < displacement_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            < displacement_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement_stats_df.loc[
            displacement_stats_df["centroid_y"]
            < displacement_stats_df["centroid_y"].median()
        ].v_mean,
        s=2,  # displacement_stats_df.loc[displacement_stats_df['centroid_y'] < displacement_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[1].grid()
    ax[1].set_ylabel("Elevation (m)", fontsize=16)
    h1 = plt.colorbar(im1, ax=ax[1], orientation="horizontal", shrink=0.8)
    h1.set_label("Southern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    fig.suptitle(
        r"Connected Components $> 1e4 m^2$: Northern and Southern Profiles", fontsize=21
    )
    fig.savefig(ccprofile_pngfn, dpi=300)
    plt.close()
    #
    ccprofile_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_CC1e5m2_E_to_W.png"
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    im0 = ax[0].scatter(
        displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            >= displacement1e5m2_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            >= displacement1e5m2_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            >= displacement1e5m2_stats_df["centroid_y"].median()
        ].v_mean,
        s=5,  # displacement1e5m2_stats_df.loc[displacement1e5m2_stats_df['centroid_y'] >= displacement1e5m2_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[0].grid()
    ax[0].set_ylabel("Elevation (m)", fontsize=16)
    h0 = plt.colorbar(im0, ax=ax[0], orientation="horizontal", shrink=0.8)
    h0.set_label("Northern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    im1 = ax[1].scatter(
        displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            < displacement1e5m2_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            < displacement1e5m2_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement1e5m2_stats_df.loc[
            displacement1e5m2_stats_df["centroid_y"]
            < displacement1e5m2_stats_df["centroid_y"].median()
        ].v_mean,
        s=5,  # displacement1e5m2_stats_df.loc[displacement1e5m2_stats_df['centroid_y'] < displacement1e5m2_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[1].grid()
    ax[1].set_ylabel("Elevation (m)", fontsize=16)
    h1 = plt.colorbar(im1, ax=ax[1], orientation="horizontal", shrink=0.8)
    h1.set_label("Southern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    fig.suptitle(
        r"Connected Components $> 1e5 m^2$: Northern and Southern Profiles", fontsize=21
    )
    fig.savefig(ccprofile_pngfn, dpi=300)
    plt.close()
    #
    ccprofile_pngfn = "P231_to_P001R077_CORR_os05_bs61_sr06_ms05_CC1e6m2_E_to_W.png"
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(16, 9),
        dpi=300,
        layout="constrained",
        sharex=True,
    )
    im0 = ax[0].scatter(
        displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            >= displacement1e6m2_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            >= displacement1e6m2_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            >= displacement1e6m2_stats_df["centroid_y"].median()
        ].v_mean,
        s=5,  # displacement1e6m2_stats_df.loc[displacement1e6m2_stats_df['centroid_y'] >= displacement1e6m2_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[0].grid()
    ax[0].set_ylabel("Elevation (m)", fontsize=16)
    h0 = plt.colorbar(im0, ax=ax[0], orientation="horizontal", shrink=0.8)
    h0.set_label("Northern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    im1 = ax[1].scatter(
        displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            < displacement1e6m2_stats_df["centroid_y"].median()
        ].centroid_x
        / 1e3,
        displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            < displacement1e6m2_stats_df["centroid_y"].median()
        ].dem_mean,
        c=displacement1e6m2_stats_df.loc[
            displacement1e6m2_stats_df["centroid_y"]
            < displacement1e6m2_stats_df["centroid_y"].median()
        ].v_mean,
        s=5,  # displacement1e6m2_stats_df.loc[displacement1e6m2_stats_df['centroid_y'] < displacement1e6m2_stats_df['centroid_y'].median()].area_m2/1e6,
        cmap="viridis_r",
        vmin=0.1,
        vmax=0.8,
    )
    ax[1].grid()
    ax[1].set_ylabel("Elevation (m)", fontsize=16)
    h1 = plt.colorbar(im1, ax=ax[1], orientation="horizontal", shrink=0.8)
    h1.set_label("Southern half mean velocity (m/y)", fontsize=12)
    ax[1].set_xlabel("UTM-X (km)", fontsize=16)
    fig.suptitle(
        r"Connected Components $> 1e6 m^2$: Northern and Southern Profiles", fontsize=21
    )
    fig.savefig(ccprofile_pngfn, dpi=300)
    plt.close()


def gaussian_filter_nan(displacement_my, sigma=2, truncate=4):
    # Gaussian Filter that ignores NaNs. First replaces NaNs with zeros and then uses a second run on a binary mask to remove the effect of 0.
    V = displacement_my.copy()
    V[np.isnan(displacement_my)] = 0
    VV = gaussian_filter(V, sigma=sigma, truncate=truncate, mode="nearest")
    W = 0 * displacement_my.copy() + 1
    W[np.isnan(displacement_my)] = 0
    WW = gaussian_filter(W, sigma=sigma, truncate=truncate, mode="nearest")
    return VV / WW


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    dem_fname = "COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif"
    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )
    displacement_fn = "CORR_os05_bs91_sr06_ms05_withSHADOWMASK/CORR_os05_bs91_sr06_ms05_median_velocity_magnitude_mmy.tif"
    logging.info("Loading %s" % displacement_fn)
    displacement_my, displacement_ds_gt, displacement_ds_proj, displacement_epsg = (
        load_Landsat_tif(displacement_fn)
    )
    # displacement_variance_fn = "/home/bodo/Dropbox/foo/P231_to_P001R077_CORR_os05_bs61_sr06_ms05_variance_magnitude_my.tif"
    # logging.info("Loading %s" % displacement_variance_fn)
    # (
    #     displacement_variance_my,
    #     displacement_variance_ds_gt,
    #     displacement_variance_ds_proj,
    #     displacement_variance_epsg,
    # ) = load_Landsat_tif(displacement_variance_fn)
    nre_fn = "CORR_os05_bs91_sr06_ms05_withSHADOWMASK/CORR_os05_bs91_sr06_ms05_nre_velocity.tif"
    logging.info("Loading %s" % nre_fn)
    (
        nre,
        nre_ds_gt,
        nre_ds_proj,
        nre_epsg,
    ) = load_Landsat_tif(nre_fn)
    nre[nre == 0] = np.nan
    nre[nre == 255] = np.nan

    logging.info("Gaussian Filtering of velocity magnitude")
    # displacement_my = gaussian_filter(displacement_my, sigma=3, mode="nearest")
    displacement_my = gaussian_filter_nan(displacement_my, sigma=1, truncate=3)

    plot_3panel_overview(
        dem[::10, ::10],
        dem_hs[::10, ::10],
        displacement_my[::10, ::10],
        nre[::10, ::10],
        "P231R077_CORR_os05_bs91_sr06_ms05_SHADOWMASK_3panel_overview.png",
    )
    plot_3profiles_overview()
    plot_3profiles_values()
    plot_histogram()

    #
    # connect component analysis
    logging.info("Finding connected components")
    v_threshold = 0.1
    displacement_my_t01 = displacement_my.copy()
    displacement_my_t01[displacement_my_t01 >= v_threshold] = 1
    displacement_my_t01[displacement_my_t01 < v_threshold] = 0
    displacement_my_t01[np.isnan(displacement_my_t01)] = 0
    displacement_my_t01 = displacement_my_t01.astype(np.bool_)
    logging.info("Calculating regionprops for connected component labels")
    min_area = 1e4
    min_size = int(np.round(min_area / (displacement_ds_gt[1] * displacement_ds_gt[1])))
    displacement_my_t01_bw1e4 = morphology.remove_small_objects(
        displacement_my_t01, min_size=min_size, connectivity=2
    )
    displacement_my_t01_bw1e4 = binary_fill_holes(displacement_my_t01_bw1e4)
    displacement_my_t01_bw1e4_labels = measure.label(
        displacement_my_t01_bw1e4, background=0
    )  # same image_binary as above
    displacement_my_t01_bw1e4_labels_props_df = pd.DataFrame(
        measure.regionprops_table(
            displacement_my_t01_bw1e4_labels,
            properties=("centroid", "area", "coords", "area_filled", "bbox"),
        )
    )

    # iterate through each connected component and extract relevant stats
    utm_x = np.arange(
        displacement_ds_gt[0],
        displacement_ds_gt[0] + (displacement_ds_gt[1] * displacement_my.shape[1] - 1),
        displacement_ds_gt[1],
    )
    utm_y = np.arange(
        displacement_ds_gt[3],
        displacement_ds_gt[3] + (displacement_ds_gt[5] * displacement_my.shape[0]),
        displacement_ds_gt[5],
    )
    displacement_stats_table = []
    # outline_x_coords = []
    # outline_y_coords = []
    for i in tqdm.tqdm(range(len(displacement_my_t01_bw1e4_labels_props_df))):
        cdf = displacement_my_t01_bw1e4_labels_props_df.iloc[i]
        area_m2 = cdf["area"] * displacement_ds_gt[1] ** 2
        area_filled_m2 = cdf["area_filled"] * displacement_ds_gt[1] ** 2
        if area_m2 > min_area:
            utm_x_centroid = utm_x[int(np.round(cdf["centroid-1"]))]
            utm_y_centroid = utm_y[int(np.round(cdf["centroid-0"]))]
            xpixels = cdf.coords[:, 0]
            ypixels = cdf.coords[:, 1]
            xy_image = np.zeros(displacement_my_t01_bw1e4_labels.shape, dtype=np.bool_)
            xy_image[xpixels, ypixels] = 1
            # this is a fast way of obtaining outline of label:
            # xy_image_outline = xy_image ^ binary_erosion(xy_image)
            # # this is very slow:
            # xy_image_cnt = measure.find_contours(xy_image)
            # # largest polygon stored on first position
            # outline_x = utm_x[np.int32(np.round(xy_image_cnt[0][:,1]))]
            # outline_x_coords.append(outline_x)
            # outline_y = utm_y[np.int32(np.round(xy_image_cnt[0][:,0]))]
            # outline_y_coords.append(outline_y)
            bbox_x = np.array([cdf["bbox-1"], cdf["bbox-3"]])
            bbox_y = np.array([cdf["bbox-0"], cdf["bbox-2"]])
            bbox_x_coords = np.array([utm_x[cdf["bbox-1"]], utm_x[cdf["bbox-3"]]])
            bbox_y_coords = np.array([utm_y[cdf["bbox-0"]], utm_y[cdf["bbox-2"]]])
            cdem = dem[cdf.coords[:, 0], cdf.coords[:, 1]]
            dem_stats = np.array(
                [
                    np.mean(cdem),
                    np.var(cdem),
                    np.median(cdem),
                    np.percentile(cdem, 25),
                    np.percentile(cdem, 75),
                ]
            )
            cslope = dem_slope[cdf.coords[:, 0], cdf.coords[:, 1]]
            slope_stats = np.array(
                [
                    np.mean(cslope),
                    np.var(cslope),
                    np.median(cslope),
                    np.percentile(cslope, 25),
                    np.percentile(cslope, 75),
                ]
            )
            cnre = nre[cdf.coords[:, 0], cdf.coords[:, 1]]
            nre_stats = np.array(
                [
                    np.nanmean(cnre),
                    np.nanmax(cnre),
                    np.nanmin(cnre),
                ]
            )
            cdisplacement = displacement_my[cdf.coords[:, 0], cdf.coords[:, 1]]
            displacement_stats = np.array(
                [
                    np.mean(cdisplacement),
                    np.var(cdisplacement),
                    np.median(cdisplacement),
                    np.percentile(cdisplacement, 25),
                    np.percentile(cdisplacement, 75),
                ]
            )
            caspect = dem_aspect[cdf.coords[:, 0], cdf.coords[:, 1]]
            aspect_stats = np.array(
                [
                    np.mean(caspect),
                    np.var(caspect),
                    np.median(caspect),
                    np.percentile(caspect, 25),
                    np.percentile(caspect, 75),
                ]
            )
            displacement_stats_table.append(
                np.r_[
                    i,
                    utm_x_centroid,
                    utm_y_centroid,
                    area_m2,
                    area_filled_m2,
                    bbox_x,
                    bbox_y,
                    bbox_x_coords,
                    bbox_y_coords,
                    dem_stats,
                    slope_stats,
                    aspect_stats,
                    displacement_stats,
                    nre_stats,
                ]
            )

    displacement_stats_df = pd.DataFrame(
        data=np.array(displacement_stats_table)[:, 1:],
        index=np.array(displacement_stats_table)[:, 0],
        columns=[
            "centroid_x",
            "centroid_y",
            "area_m2",
            "area_filled_m2",
            "bbox_x1",
            "bbox_x2",
            "bbox_y1",
            "bbox_y2",
            "bbox_x_coord1",
            "bbox_x_coord2",
            "bbox_y_coord1",
            "bbox_y_coord2",
            "dem_mean",
            "dem_var",
            "dem_median",
            "dem_p25",
            "dem_p75",
            "slope_mean",
            "slope_var",
            "slope_median",
            "slope_p25",
            "slope_p75",
            "aspect_mean",
            "aspect_var",
            "aspect_median",
            "aspect_p25",
            "aspect_p75",
            "v_mean",
            "v_var",
            "v_median",
            "v_p25",
            "v_p75",
            "nre_mean",
            "nre_max",
            "nre_min",
        ],
    )
    # removal of large area - likely oceans or lakes
    (idx2remove,) = np.where(displacement_stats_df["area_m2"] > 1e7)
    displacement_stats_df.drop(index=idx2remove, inplace=True)

    # displacement_stats_df.loc[
    #     (displacement_stats_df["v_median"] > 0.2)
    #     & (displacement_stats_df["area_m2"] > 1e5) & (displacement_stats_df['nre_min'] > 100)
    # ]
    # displacement_stats_df.loc[
    #     (displacement_stats_df["v_median"] > 0.5)
    #     & (displacement_stats_df["area_m2"] > 1e6) & (displacement_stats_df['nre_min'] > 50)
    # ]
    # df_clip = displacement_stats_df.loc[displacement_stats_df.index == 20355.0] #Mina Purna
    # i =0
    # x1, x2 = int(df_clip.iloc[i]["bbox_x1"]), int(df_clip.iloc[i]["bbox_x2"])
    # y1, y2 = int(df_clip.iloc[i]["bbox_y1"]), int(df_clip.iloc[i]["bbox_y2"])
    # np.savetxt(
    #     "x1_x2_y1_y2_coordinates.txt", np.c_[x1, x2, y1, y2], fmt="%d", delimiter=","
    # )
    # displacement_my_t01_bw1e4_labels[x1:x2, y1:y2]

    # if we have list of coordinates of outline, create polygon with:
    # polygon_geom = Polygon(zip(lon_point_list, lat_point_list))
    # polygon = gpd.GeoDataFrame(index=[0], crs='EPSG:32619', geometry=[polygon_geom])
    # create bounding box polyong
    # polygon_geom = Polygon(zip(lon_point_list, lat_point_list))
    # polygon = gpd.GeoDataFrame(index=[0], crs='EPSG:32619', geometry=[polygon_geom])
    logging.info("Building bounding box geometry")
    bbox_polygon_list = []
    for i in range(len(displacement_stats_df)):
        minx = displacement_stats_df.iloc[i]["bbox_x_coord1"]
        miny = displacement_stats_df.iloc[i]["bbox_y_coord1"]
        maxx = displacement_stats_df.iloc[i]["bbox_x_coord2"]
        maxy = displacement_stats_df.iloc[i]["bbox_y_coord2"]
        bbox_tuple = (minx, miny, maxx, maxy)
        bbox_polygon = geometry.box(*bbox_tuple)
        bbox_polygon_list.append(bbox_polygon)

    displacement_stats_bbox_gdf = gpd.GeoDataFrame(
        displacement_stats_df, geometry=bbox_polygon_list, crs="EPSG:32620"
    )
    displacement_stats_bbox_gdf.to_file(
        "P231R077_CORR_os05_bs91_sr06_ms05_cc1e4m2_bbox.gpkg"
    )
    # remove low-slope areas
    # displacement_stats_df.loc[displacement_stats_df['slope_mean'] < 7]
    displacement_stats_gdf = gpd.GeoDataFrame(
        displacement_stats_df,
        geometry=gpd.points_from_xy(
            displacement_stats_df.centroid_x, displacement_stats_df.centroid_y
        ),
        crs="EPSG:32620",
    )
    displacement_stats_gdf.to_file("P231R077_CORR_os05_bs91_sr06_ms05_cc1e4m2.gpkg")

    displacement1e5m2_stats_df = displacement_stats_df.loc[
        displacement_stats_df["area_m2"] > 1e5
    ]
    displacement1e6m2_stats_df = displacement_stats_df.loc[
        displacement_stats_df["area_m2"] > 1e6
    ]
    plot_CC_profiles()
