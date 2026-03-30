import numpy as np
import numba as nb
import h5py
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.cbook import get_sample_data
from matplotlib.colors import LightSource
import os, logging, tqdm, warnings, argparse, sys, time
from scipy.interpolate import LinearNDInterpolator


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


def tile_with_overlap(x, tile_size=128, overlap=24):
    iheight = x.shape[0]
    iwidth = x.shape[1]
    # pad overlap to all sides of array
    x = np.pad(
        x,
        ((overlap, overlap), (overlap, overlap)),
        mode="constant",
        constant_values=np.nan,
    )
    height = x.shape[0]
    width = x.shape[1]
    patch_size = tile_size + (overlap * 2)
    pad_height = (patch_size - (height % patch_size)) % patch_size
    pad_width = (patch_size - (width % patch_size)) % patch_size
    # Apply padding to the image
    x = np.pad(
        x, ((0, pad_height), (0, pad_width)), mode="constant", constant_values=np.nan
    )
    assert x.shape[0] % patch_size == 0
    assert x.shape[1] % patch_size == 0
    foo = np.lib.stride_tricks.sliding_window_view(x, (patch_size, patch_size))[
        ::tile_size, ::tile_size
    ]
    return (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        x.shape[0],
        x.shape[1],
        foo.shape[0],
        foo.shape[1],
        foo.shape[2],
        foo.reshape((foo.shape[0] * foo.shape[1], foo.shape[2], foo.shape[3])),
    )


@nb.njit(parallel=True)
def get_tile_centerpoints(tile):
    tile_median = np.empty(tile.shape[0], dtype=np.float32)
    tile_median.fill(np.nan)
    tile_mean = np.empty(tile.shape[0], dtype=np.float32)
    tile_mean.fill(np.nan)
    tile_min = np.empty(tile.shape[0], dtype=np.float32)
    tile_min.fill(np.nan)
    tile_max = np.empty(tile.shape[0], dtype=np.float32)
    tile_max.fill(np.nan)
    tile_p25 = np.empty(tile.shape[0], dtype=np.float32)
    tile_p25.fill(np.nan)
    tile_p75 = np.empty(tile.shape[0], dtype=np.float32)
    tile_p75.fill(np.nan)
    for i in nb.prange(tile.shape[0]):
        tile_median[i] = np.nanmedian(tile[i, :, :])
        tile_mean[i] = np.nanmean(tile[i, :, :])
        tile_min[i] = np.nanmin(tile[i, :, :])
        tile_max[i] = np.nanmax(tile[i, :, :])
        tile_p25[i], tile_p75[i] = np.nanpercentile(tile[i, :, :], [25, 75])
    return tile_median, tile_mean, tile_min, tile_max, tile_p25, tile_p75


def plot_tile_overview(
    offset, offset_lineari, offset_tile_mean, suptitle, tiles_overview_output_fn
):
    # making plot of data and tiling setup
    nr_rows = 2
    nr_cols = 2
    fig, ax = plt.subplots(
        nr_cols,
        nr_rows,
        sharex=True,
        sharey=True,
        figsize=(16, 12),
        dpi=300,
        layout="constrained",
    )
    ax[0, 0].imshow(
        dem_hs,
        extent=dem_extent,
        cmap="gray",
    )
    im0 = ax[0, 0].imshow(
        dem,
        extent=dem_extent,
        cmap="gist_earth",
        vmin=np.nanpercentile(dem, 2),
        vmax=np.nanpercentile(dem, 98),
        alpha=0.7,
    )
    h0 = plt.colorbar(im0, ax=ax[0, 0], orientation="vertical")
    h0.set_label("Elevation (m)")
    for i in range(0, len(coord0_tile_min), 1):
        tile_width = coord0_tile_max[i] - coord0_tile_min[i]
        tile_height = coord1_tile_max[i] - coord1_tile_min[i]
        # xy, width, height
        rect = Rectangle(
            (coord0_tile_min[i], coord1_tile_min[i]),
            width=tile_width,
            height=tile_height,
            linewidth=1,
            edgecolor="black",
            facecolor=None,
            fill=False,
            alpha=1,
        )
        ax[0, 0].add_patch(rect)
    ax[0, 0].set_aspect("equal", "box")
    ax[0, 0].plot(coord0_tile_median, coord1_tile_median, "co", color="k", ms=3)
    ax[0, 0].set_ylabel("UTM-Y")
    #
    ax[1, 0].imshow(
        dem_hs,
        extent=dem_extent,
        cmap="gray",
    )
    im0 = ax[1, 0].imshow(
        offset_lineari,
        extent=dem_extent,
        cmap="Spectral",
        vmin=-0.2,
        vmax=0.2,
        alpha=0.7,
    )
    im1 = ax[1, 0].scatter(
        coord0_tile_median,
        coord1_tile_median,
        s=35,
        c=offset_tile_mean,
        cmap="Spectral",
        edgecolors="black",
        vmin=-0.2,
        vmax=0.2,
        alpha=0.7,
    )
    h1 = plt.colorbar(im1, ax=ax[1, 0])
    h1.set_label("Interpolated Offset (m/y)")
    ax[1, 0].set_aspect("equal", "box")
    ax[1, 0].set_ylabel("UTM-Y")
    #
    ax[0, 1].imshow(
        dem_hs,
        extent=dem_extent,
        cmap="gray",
    )
    im2 = ax[0, 1].imshow(
        offset,
        cmap="Spectral",
        vmin=-0.2,
        vmax=0.2,
        extent=dem_extent,
        alpha=0.7,
    )
    h2 = plt.colorbar(im2, ax=ax[0, 1])
    h2.set_label("Offset (m/y)")
    ax[0, 1].plot(coord0_tile_median, coord1_tile_median, "co", color="k", ms=3)
    ax[0, 1].set_aspect("equal", "box")
    #
    ax[1, 1].imshow(
        dem_hs,
        extent=dem_extent,
        cmap="gray",
    )
    im3 = ax[1, 1].imshow(
        offset - offset_lineari,
        cmap="Spectral",
        vmin=-0.2,
        vmax=0.2,
        extent=dem_extent,
        alpha=0.7,
    )
    h3 = plt.colorbar(im3, ax=ax[1, 1])
    h3.set_label("Corrected offset (m/y)")
    ax[1, 1].set_aspect("equal", "box")
    ax[1, 1].set_xlabel("UTM-X")
    fig.suptitle(suptitle, fontsize=14)
    fig.savefig(tiles_overview_output_fn, dpi=300)
    plt.close()


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")
    # args = cmdLineParser()

    tile_size = 1500

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )

    minx = dem_gt[0]
    maxy = dem_gt[3]
    maxx = minx + dem_gt[1] * dem.shape[1]
    miny = maxy + dem_gt[5] * dem.shape[0]
    # extent=[longitude_top_left,longitude_top_right,latitude_bottom_left,latitude_top_left]
    dem_extent = [
        minx,
        maxx,
        miny,
        maxy,
    ]
    dem_coord0, dem_coord1 = np.meshgrid(
        np.arange(minx, maxx, dem_gt[1]),
        np.arange(miny, maxy, dem_gt[1]),
    )
    dem_coord0 = dem_coord0.astype(np.float32)
    dem_coord1 = np.flipud(dem_coord1.astype(np.float32))
    #
    logging.info("Tiling DEM")
    (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        oheight,
        owidth,
        dim0,
        dim1,
        dim2,
        dem_tiles,
    ) = tile_with_overlap(dem, tile_size=tile_size, overlap=100)
    (
        DEM_tile_median,
        DEM_tile_mean,
        DEM_tile_min,
        DEM_tile_max,
        DEM_tile_p25,
        DEM_tile_p75,
    ) = get_tile_centerpoints(dem_tiles)
    #
    logging.info("Tiling UTM-X")
    (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        oheight,
        owidth,
        dim0,
        dim1,
        dim2,
        coord0_tiles,
    ) = tile_with_overlap(dem_coord0, tile_size=tile_size, overlap=100)
    (
        coord0_tile_median,
        coord0_tile_mean,
        coord0_tile_min,
        coord0_tile_max,
        coord0_tile_p25,
        coord0_tile_p75,
    ) = get_tile_centerpoints(coord0_tiles)
    #
    logging.info("Tiling UTM-Y")
    (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        oheight,
        owidth,
        dim0,
        dim1,
        dim2,
        coord1_tiles,
    ) = tile_with_overlap(dem_coord1, tile_size=tile_size, overlap=100)
    (
        coord1_tile_median,
        coord1_tile_mean,
        coord1_tile_min,
        coord1_tile_max,
        coord1_tile_p25,
        coord1_tile_p75,
    ) = get_tile_centerpoints(coord1_tiles)
    #
    logging.info("Tiling offset array ")
    (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        oheight,
        owidth,
        dim0,
        dim1,
        dim2,
        u_tiles,
    ) = tile_with_overlap(u, tile_size=tile_size, overlap=100)
    u_tile_median, u_tile_mean, u_tile_min, u_tile_max, u_tile_p25, u_tile_p75 = (
        get_tile_centerpoints(u_tiles)
    )

    logging.info("LinearNDInterpolator of mean offset")
    Linear_interpolator = LinearNDInterpolator(
        (coord0_tile_median, coord1_tile_median), u_tile_mean
    )
    u_tile_mean_linear = Linear_interpolator((dem_coord0, dem_coord1))
    # u_tile_mean_linear[np.isnan(u)] = np.nan

    tiles_overview_output_fn = "overview_test.png"
    suptitle = "Name"
    plot_tile_overview(
        offset=u,
        offset_lineari=u_tile_mean_linear,
        offset_tile_mean=u_tile_mean,
        suptitle=suptitle,
        tiles_overview_output_fn=tiles_overview_output_fn,
    )

    tiles_regression_output_fn = "test_regression_full.png"
    fig, ax = plt.subplots(
        1,
        1,
        sharex=True,
        sharey=True,
        figsize=(12, 9),
        dpi=300,
        layout="constrained",
    )
    ax.plot(
        dem[::5, ::5].ravel(),
        u[::5, ::5].ravel()
        + (np.random.random(u[::5, ::5].ravel().shape[0]) / 10)
        - 0.5,
        "k.",
    )
    ax.grid()
    ax.set_ylabel("offset (m/y)")
    fig.savefig(tiles_regression_output_fn, dpi=300)
    plt.close()

    tiles_regression_output_fn = "test_regression.png"
    fig, ax = plt.subplots(
        2,
        2,
        sharex=True,
        sharey=True,
        figsize=(12, 9),
        dpi=300,
        layout="constrained",
    )
    i = 0
    ax[0, 0].plot(dem_tiles[i, :, :].ravel(), u_tiles[i, :, :].ravel(), "k.")
    ax[0, 0].grid()
    ax[0, 0].set_ylabel("offset (m/y)")
    i = 1
    ax[0, 1].plot(dem_tiles[i, :, :].ravel(), u_tiles[i, :, :].ravel(), "k.")
    ax[0, 1].grid()
    i = 2
    ax[1, 0].plot(dem_tiles[i, :, :].ravel(), u_tiles[i, :, :].ravel(), "k.")
    ax[1, 0].grid()
    i = 3
    ax[1, 1].plot(dem_tiles[i, :, :].ravel(), u_tiles[i, :, :].ravel(), "k.")
    ax[1, 1].grid()
    fig.suptitle("Tiling and regression plots", fontsize=12)
    fig.savefig(tiles_regression_output_fn, dpi=300)
    plt.close()
