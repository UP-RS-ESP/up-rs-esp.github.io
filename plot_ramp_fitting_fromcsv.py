from datetime import date
import numpy as np
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

gdal.UseExceptions()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def ArithmeticDegree_to_GeographicDegree(angle):
    return (-(angle - 90)) % 360


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


def load_offset_tif(fname):
    offset_ds = gdal.Open(fname)
    offset_ds_gt = offset_ds.GetGeoTransform()
    offset_ds_proj = offset_ds.GetProjection()
    epsg = int(osr.SpatialReference(wkt=offset_ds_proj).GetAttrValue("AUTHORITY", 1))
    offset = np.array(offset_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    offset[offset == -128] = np.nan
    offset_ds = None
    return offset, offset_ds_gt, offset_ds_proj, epsg


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


def get_deltaT_from_filename(filename):
    date1 = pd.to_datetime(os.path.basename(filename).split("_")[0])
    date2 = pd.to_datetime(os.path.basename(filename).split("_")[1])
    difference_in_years = relativedelta(date2, date1).years
    difference_in_days = relativedelta(date2, date1).days / 365.25
    difference_in_years += difference_in_days
    deltaT_y = difference_in_years
    return deltaT_y, date1, date2


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


def load_u_file(u_file):
    # open first file to get file dimension
    u, u_ds_gt, u_ds_proj, u_epsg = load_offset_tif(u_file)
    deltaT, date1, date2 = get_deltaT_from_filename(u_file)
    return deltaT, date1, date2, u, u_ds_gt, u_epsg


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


def create_p1_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    logging.info("Data directory is %s" % (dirname))
    oversampling = int(os.path.basename(dirname).split("_")[1][2:])
    block_size = int(os.path.basename(dirname).split("_")[2][2:])
    search_radius = int(os.path.basename(dirname).split("_")[3][2:])
    matching_step = int(os.path.basename(dirname).split("_")[4][2:])
    outfile_u = []
    outfile_v = []
    for i in range(len(date_pairs)):
        outfname_u = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_u.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_u = os.path.join(dirname + "u_p1", outfname_u)
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
        outfname_v = os.path.join(dirname + "v_p1", outfname_v)
        if not os.path.exists(outfname_v):
            logging.info("%s does not exists" % outfname_v)
        if not os.path.exists(outfname_u) or not os.path.exists(outfname_v):
            logging.info(
                "Not all u and v files exists for that date. Not adding date %d_%d to list."
                % (date_pairs[i, 0], date_pairs[i, 1])
            )
        else:
            outfile_u.append(outfname_u)
            outfile_v.append(outfname_v)
    return outfile_u, outfile_v


def create_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    logging.info("Data directory is %s" % (dirname))
    oversampling = int(os.path.basename(dirname).split("_")[1][2:])
    block_size = int(os.path.basename(dirname).split("_")[2][2:])
    search_radius = int(os.path.basename(dirname).split("_")[3][2:])
    matching_step = int(os.path.basename(dirname).split("_")[4][2:])
    outfile_u = []
    outfile_v = []
    for i in range(len(date_pairs)):
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
        if not os.path.exists(outfname_u) or not os.path.exists(outfname_v):
            logging.info(
                "Not all u and v files exists for that date. Not adding date %d_%d to list."
                % (date_pairs[i, 0], date_pairs[i, 1])
            )
        else:
            outfile_u.append(outfname_u)
            outfile_v.append(outfname_v)
    return outfile_u, outfile_v


def plot_ramp_overview(
    dem_hs,
    offset_u,
    ramp_u,
    corrected_u,
    offset_v,
    ramp_v,
    corrected_v,
    suptitle,
    ramp_overview_output_fn,
):
    nr_rows = 2
    nr_cols = 3
    fig, ax = plt.subplots(
        nr_rows,
        nr_cols,
        sharex=True,
        sharey=True,
        figsize=(16, 12),
        dpi=300,
        layout="constrained",
    )
    ax[0, 0].imshow(
        dem_hs,
        cmap="gray",
    )
    im0 = ax[0, 0].imshow(
        offset_u,
        cmap="Spectral",
        vmin=-0.5,
        vmax=0.5,
        alpha=0.7,
    )
    h0 = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal", shrink=0.8)
    h0.set_label("offset u (m/y)")
    ax[0, 0].get_xaxis().set_ticks([])
    ax[0, 0].get_yaxis().set_ticks([])
    #
    ax[1, 0].imshow(
        dem_hs,
        cmap="gray",
    )
    im1 = ax[1, 0].imshow(
        offset_v,
        cmap="Spectral",
        vmin=-0.5,
        vmax=0.5,
        alpha=0.7,
    )
    h1 = plt.colorbar(im1, ax=ax[1, 0], orientation="horizontal", shrink=0.8)
    h1.set_label("offset v (m/y)")
    ax[1, 0].get_xaxis().set_ticks([])
    ax[1, 0].get_yaxis().set_ticks([])
    #
    ax[0, 1].imshow(
        dem_hs,
        cmap="gray",
    )
    im2 = ax[0, 1].imshow(
        ramp_u,
        cmap="PiYG",
        vmin=-0.2,
        vmax=0.2,
        alpha=0.7,
    )
    h2 = plt.colorbar(im2, ax=ax[0, 1], orientation="horizontal", shrink=0.8)
    h2.set_label("ramp u")
    ax[0, 1].get_xaxis().set_ticks([])
    ax[0, 1].get_yaxis().set_ticks([])
    #
    ax[1, 1].imshow(
        dem_hs,
        cmap="gray",
    )
    im3 = ax[1, 1].imshow(
        ramp_v,
        cmap="PiYG",
        vmin=-0.2,
        vmax=0.2,
        alpha=0.7,
    )
    h3 = plt.colorbar(im3, ax=ax[1, 1], orientation="horizontal", shrink=0.8)
    h3.set_label("ramp v")
    ax[1, 1].get_xaxis().set_ticks([])
    ax[1, 1].get_yaxis().set_ticks([])
    #
    ax[0, 2].imshow(
        dem_hs,
        cmap="gray",
    )
    im4 = ax[0, 2].imshow(
        corrected_u,
        cmap="Spectral",
        vmin=-0.5,
        vmax=0.5,
        alpha=0.7,
    )
    h2 = plt.colorbar(im4, ax=ax[0, 2], orientation="horizontal", shrink=0.8)
    h2.set_label("corrected u (m/y)")
    ax[0, 2].get_xaxis().set_ticks([])
    ax[0, 2].get_yaxis().set_ticks([])
    #
    ax[1, 2].imshow(
        dem_hs,
        cmap="gray",
    )
    im5 = ax[1, 2].imshow(
        corrected_v,
        cmap="Spectral",
        vmin=-0.5,
        vmax=0.5,
        alpha=0.7,
    )
    h3 = plt.colorbar(im5, ax=ax[1, 2], orientation="horizontal", shrink=0.8)
    h3.set_label("corrected v (m/y)")
    ax[1, 2].get_xaxis().set_ticks([])
    ax[1, 2].get_yaxis().set_ticks([])
    fig.suptitle(suptitle, fontsize=14)
    fig.savefig(ramp_overview_output_fn, dpi=300)
    plt.close()


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")

    dirprefix = sys.argv[1]
    dem_fname = sys.argv[2]
    csv_fname = sys.argv[3]

    # dirprefix = "/raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_"
    # dem_fname = (
    #     "/raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif"
    # )
    # csv_fname = "corr_dates_sd1_cc20_B"
    # python run_stack_block_matching_fromcsv.py  \
    # CORR_os05_bs91_sr06_ms05 \
    # CORR_os01_bs11_sr03_ms01/ \
    # CORR_os05_bs91_sr06_ms05_ \
    # COP15_DEM_NW_ARGENTINA_UTM20_P231R077.tif \
    # corr_dates_sd1_cc30_short
    # dirprefix = "/raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_"
    # dem_fname = (
    #     "/raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif"
    # )
    # csv_fname = "corr_dates_sd1_cc20_B"
    filelist_fn = (
        os.path.basename(dirprefix) + os.path.basename(csv_fname) + "ramp.filelist"
    )

    ramp_overview_pngdir = dirprefix + "rampoverview_png"
    if not os.path.exists(ramp_overview_pngdir):
        os.mkdir(ramp_overview_pngdir)

    dem, dem_gt, dem_proj, dem_epsg, dem_aspect, dem_slope, dem_hs = (
        load_dem_aspect_slope_files(dem_fname)
    )
    dem_coord0, dem_coord1 = np.meshgrid(
        np.arange(0, dem.shape[1] * dem_gt[1], dem_gt[1]),
        np.arange(0, dem.shape[0] * dem_gt[1], dem_gt[1]),
    )
    outfile_u, outfile_v = create_fnames_from_csv(csv_fname, dirprefix)
    outfile_p1_u, outfile_p1_v = create_p1_fnames_from_csv(csv_fname, dirprefix)
    v_stats_df = pd.read_csv(
        os.path.basename(dirprefix) + os.path.basename(csv_fname) + "_v_stats.csv"
    )
    v_stats_df.set_index("filenr", inplace=True)
    u_stats_df = pd.read_csv(
        os.path.basename(dirprefix) + os.path.basename(csv_fname) + "_u_stats.csv"
    )
    u_stats_df.set_index("filenr", inplace=True)

    logging.info("Loading and plotting %d files" % len(outfile_u))
    fname_list = []
    for i in tqdm.tqdm(range(len(outfile_u))):
        ramp_overview_output_fn = (
            os.path.basename(outfile_u[i])[:-5] + "rampoverview.png"
        )
        ramp_overview_output_fn = os.path.join(
            ramp_overview_pngdir, ramp_overview_output_fn
        )
        fname_list.append(ramp_overview_output_fn)
        if os.path.exists(ramp_overview_output_fn):
            continue

        deltaT, date1, date2, u, u_ds_gt, u_epsg = load_u_file(outfile_u[i])
        # deltaT, date1, date2, u_p1, u_ds_gt, u_epsg = load_u_file(outfile_p1_u[i])
        deltaT, date1, date2, v, u_ds_gt, u_epsg = load_u_file(outfile_v[i])
        # deltaT, date1, date2, v_p1, u_ds_gt, u_epsg = load_u_file(outfile_p1_v[i])

        U_xy = (
            u_stats_df["U_0"].iloc[i] * dem_coord0
            + u_stats_df["U_1"].iloc[i] * dem_coord1
            + u_stats_df["U_2"].iloc[i]
        )
        p1_du = u - U_xy
        V_xy = (
            v_stats_df["V_0"].iloc[i] * dem_coord0
            + v_stats_df["V_1"].iloc[i] * dem_coord1
            + v_stats_df["V_2"].iloc[i]
        )
        p1_dv = v - V_xy

        suptitle = os.path.basename(outfile_u[i])[:-6]
        plot_ramp_overview(
            dem_hs,
            offset_u=u,
            ramp_u=U_xy,
            corrected_u=p1_du,
            offset_v=v,
            ramp_v=V_xy,
            corrected_v=p1_dv,
            suptitle=suptitle,
            ramp_overview_output_fn=ramp_overview_output_fn,
        )

    with open(filelist_fn, "w") as f:
        for line in fname_list:
            f.write(f"{line}\n")
