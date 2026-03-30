import numpy as np
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm, warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from plot_hist import plot_hist
from scipy.stats import gaussian_kde as kde
from scipy.spatial import cKDTree

gdal.UseExceptions()
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def calculate_point_density(points, radius=10000):
    # Build the cKDTree
    tree = cKDTree(points)
    # Count neighbors within radius for each point
    # query_ball_point returns indices of neighbors
    # counts = [len(idx) for idx in tree.query_ball_point(points, radius)]
    idxs = tree.query_ball_point(points, radius)
    counts = np.zeros(len(idxs), dtype=np.int32)
    vel_median = np.empty(len(idxs), dtype=np.float32)
    vel_median.fill(np.nan)
    lds_area_sum = np.empty(len(idxs), dtype=np.float32)
    lds_area_sum.fill(np.nan)
    lds_area_median = np.empty(len(idxs), dtype=np.float32)
    lds_area_median.fill(np.nan)
    for i in range(len(idxs)):
        # could run this via numba
        idx = idxs[i]
        counts[i] = len(idx)
        vel_median[i] = np.median(cc_combined_gdf["v_median"].iloc[idx])
        lds_area_sum[i] = np.sum(cc_combined_gdf["area_m2"].iloc[idx])
        lds_area_median[i] = np.median(cc_combined_gdf["area_m2"].iloc[idx])
    # Calculate density (points per unit area)
    # Area for 2D is pi * r^2
    areas = np.pi * radius**2
    densities = counts / areas
    area_fraction = lds_area_sum / areas
    return densities, counts, vel_median, lds_area_sum, lds_area_median, area_fraction


def plot_area_velocity_elevation_hist():
    fig, (ax1, ax2) = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    ax1, hist, bin_edges = plot_hist(
        cc_combined_epsg4326["area_m2"].values,
        log_bins=True,
        density=True,
        bins=5,
        ax=ax1,
        color="k",
        linewidth=0.1,
        label="All Landslides",
    )
    ax1.set_yscale("log")
    ax1.grid()
    bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.0
    ax1.plot(bin_centers, hist, "o", ms=3, color="k")
    # calculate histogram for elevations above 4 km
    cc_combined_epsg4326_above4km = cc_combined_epsg4326[
        (cc_combined_epsg4326["dem_mean"] > 4000)
        & (cc_combined_epsg4326["dem_mean"] < 5000)
    ]
    _, hist4km, bin_edges4km = plot_hist(
        cc_combined_epsg4326_above4km["area_m2"].values,
        log_bins=True,
        density=True,
        bins=5,
        ax=ax1,
        color="navy",
        linewidth=0.5,
        label="Landslides from 4-5 km elevations",
    )
    bin_centers4km = (bin_edges4km[1:] + bin_edges4km[:-1]) / 2.0
    ax1.plot(bin_centers4km, hist4km, "x", ms=5, color="navy")
    # calculate histogram for elevations above 5 km
    cc_combined_epsg4326_above5km = cc_combined_epsg4326[
        cc_combined_epsg4326["dem_mean"] > 5000
    ]
    _, hist5km, bin_edges5km = plot_hist(
        cc_combined_epsg4326_above5km["area_m2"].values,
        log_bins=True,
        density=True,
        bins=5,
        ax=ax1,
        color="darkorange",
        linewidth=0.5,
        label="Landslides above 5 km elevations",
    )
    bin_centers5km = (bin_edges5km[1:] + bin_edges5km[:-1]) / 2.0
    ax1.plot(bin_centers5km, hist5km, "s", ms=5, color="darkorange")
    ax1.set_title(
        "Combined CC (n=%s): Area ($m^2$)" % f"{len(cc_combined_epsg4326):,}",
        fontsize=16,
    )
    ax1.set_xlabel("Magnitude: Area ($m^2$)", fontsize=14)
    ax1.set_ylabel("Frequency (Density)", fontsize=14)
    ax1.legend()
    vmedian = cc_combined_epsg4326["v_median"][
        ~np.isnan(cc_combined_epsg4326["v_median"])
    ].values
    ax2, hist_vel, vel_bin_edges = plot_hist(
        vmedian,
        log_bins=True,
        density=True,
        bins=10,
        ax=ax2,
        color="k",
        linewidth=0.1,
        label="All Landslides,median",
    )
    v_p75 = cc_combined_epsg4326["v_p75"][
        ~np.isnan(cc_combined_epsg4326["v_p75"])
    ].values
    ax2, hist_vel_p75, vel_p75_bin_edges = plot_hist(
        v_p75,
        log_bins=True,
        density=True,
        bins=10,
        ax=ax2,
        color="darkgreen",
        linewidth=0.5,
        label="All Landslides, p75",
    )
    vmedian4km = cc_combined_epsg4326_above4km["v_median"][
        ~np.isnan(cc_combined_epsg4326_above4km["v_median"])
    ].values
    _, hist_vel4km, vel_bin_edges4km = plot_hist(
        vmedian4km,
        log_bins=True,
        density=True,
        bins=10,
        ax=ax2,
        color="navy",
        linewidth=0.5,
        label="Landslides from 4-5 km elevations",
    )
    vmedian5km = cc_combined_epsg4326_above5km["v_median"][
        ~np.isnan(cc_combined_epsg4326_above5km["v_median"])
    ].values
    _, hist_vel5km, vel_bin_edges5km = plot_hist(
        vmedian5km,
        log_bins=True,
        density=True,
        bins=10,
        ax=ax2,
        color="darkorange",
        linewidth=0.5,
        label="Landslides above 5 km elevations",
    )
    ax2.set_yscale("log")
    ax2.grid()
    ax2.legend()
    vel_bin_centers = (vel_bin_edges[1:] + vel_bin_edges[:-1]) / 2.0
    ax2.plot(vel_bin_centers, hist_vel, "o", color="k")
    vel_bin_centers4km = (vel_bin_edges4km[1:] + vel_bin_edges4km[:-1]) / 2.0
    ax2.plot(vel_bin_centers4km, hist_vel4km, "x", color="navy")
    vel_bin_centers5km = (vel_bin_edges5km[1:] + vel_bin_edges5km[:-1]) / 2.0
    ax2.plot(vel_bin_centers5km, hist_vel5km, "s", color="darkorange")
    ax2.set_title(
        "Combined CC (n=%s): Median Velocity ($m/y$)" % f"{len(vmedian):,}", fontsize=16
    )
    ax2.set_xlabel("Magnitude: Median Velocity ($m/y$)", fontsize=14)
    ax2.set_ylabel("Frequency (Density)", fontsize=14)
    plt.rc("xtick", labelsize=12)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=12)  # fontsize of the tick labels
    fig.savefig("CC_combined_area_velocity_magfreq_elevations_mean.png", dpi=300)


def plot_area_velocity_hist():
    fig, (ax1, ax2) = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    ax1, hist, bin_edges = plot_hist(
        cc_combined_epsg4326["area_m2"].values,
        log_bins=True,
        density=True,
        bins=5,
        ax=ax1,
        color="navy",
        linewidth=0.5,
    )
    ax1.set_yscale("log")
    ax1.grid()
    bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.0
    ax1.plot(bin_centers, hist, "o", color="navy")
    ax1.set_title(
        "Combined CC (n=%s): Area ($m^2$)" % f"{len(cc_combined_epsg4326):,}",
        fontsize=16,
    )
    ax1.set_xlabel("Magnitude: Area ($m^2$)", fontsize=14)
    ax1.set_ylabel("Frequency (Density)", fontsize=14)
    vmean = cc_combined_epsg4326["v_mean"][
        ~np.isnan(cc_combined_epsg4326["v_mean"])
    ].values
    vmedian = cc_combined_epsg4326["v_median"][
        ~np.isnan(cc_combined_epsg4326["v_median"])
    ].values
    ax2, hist_vel, vel_bin_edges = plot_hist(
        vmedian,
        log_bins=True,
        density=True,
        bins=10,
        ax=ax2,
        color="darkred",
        linewidth=0.5,
    )
    ax2.set_yscale("log")
    ax2.grid()
    vel_bin_centers = (vel_bin_edges[1:] + vel_bin_edges[:-1]) / 2.0
    ax2.plot(vel_bin_centers, hist_vel, "o", color="darkred")
    ax2.set_title(
        "Combined CC (n=%s): Median Velocity ($m/y$)" % f"{len(vmedian):,}", fontsize=16
    )
    ax2.set_xlabel("Magnitude: Mean Velocity ($m/y$)", fontsize=14)
    ax2.set_ylabel("Frequency (Density)", fontsize=14)
    plt.rc("xtick", labelsize=12)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=12)  # fontsize of the tick labels
    fig.savefig("CC_combined_area_velocity_magfreq.png", dpi=300)


def plot_map_density_med_velocity(gdf_epsg4326, radius):
    points = np.c_[gdf_epsg4326.centroid.x.values, gdf_epsg4326.centroid.y.values]
    fig, (ax1, ax2) = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    im1 = ax1.scatter(
        points[:, 0],
        points[:, 1],
        s=0.5,
        c=gdf_epsg4326["LDS_density"],
        norm=matplotlib.colors.LogNorm(
            vmin=np.nanpercentile(gdf_epsg4326["LDS_density"], 2),
            vmax=np.max(gdf_epsg4326["LDS_density"]),
        ),
        cmap="viridis",
    )
    h = plt.colorbar(im1, ax=ax1, shrink=0.7, orientation="horizontal")
    h.set_label("Landslide Density (#/%.1f km2)" % ((np.pi * radius**2) / 1e6))
    ax1.grid()
    ax1.set_title(
        "Landslide Density for radius=%d km (n=%s)"
        % (radius / 1000, f"{len(cc_combined_epsg4326):,}"),
        fontsize=16,
    )
    im2 = ax2.scatter(
        points[:, 0],
        points[:, 1],
        s=0.5,
        c=gdf_epsg4326["LDS_vel_median"],
        norm=matplotlib.colors.LogNorm(
            vmin=np.nanpercentile(gdf_epsg4326["LDS_vel_median"], 2),
            vmax=1,
            # vmax=np.max(gdf_epsg4326["LDS_vel_median"]),
        ),
        cmap="magma",
    )
    ax2.grid()
    ax2.set_title(
        "Landslide Median Velocity for radius=%d km (n=%s)"
        % (radius / 1000, f"{len(cc_combined_epsg4326):,}"),
        fontsize=16,
    )
    h = plt.colorbar(im2, ax=ax2, shrink=0.7, orientation="horizontal")
    h.set_label("Landslide Median Velocity (m/y)")
    plt.rc("xtick", labelsize=12)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=12)  # fontsize of the tick labels
    fig.savefig(
        os.path.join(
            gpkg_dir, "CC_landslide_density_medianvelocity_radius%d.png" % radius
        ),
        dpi=300,
    )

def plot_slope_elevation_med_velocity(cc_combined_gdf, density_velmedian_epsg4326_gdf):
    fig, (ax1, ax2) = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained", sharey=True,
    )
    im1 = ax1.scatter(
        cc_combined_gdf.dem_mean,
        cc_combined_gdf.slope_mean,
        s=0.5,
        c=cc_combined_gdf.v_median,
        norm=matplotlib.colors.LogNorm(
            vmin=np.nanpercentile(cc_combined_gdf.v_median, 2),
            vmax=np.max(cc_combined_gdf.v_median),
        ),
        cmap="viridis",
    )
    ax1.set_xlabel('Landslide mean elevation (m)', fontsize=12)
    ax1.set_ylabel('Landslide mean slope (degree)', fontsize=12)
    h = plt.colorbar(im1, ax=ax1, shrink=0.7, orientation="horizontal")
    h.set_label("Landslide Median velocity (m/y)")
    ax1.grid()
    ax1.set_title(
        "Elevation-Slope-Median Velocity",
        fontsize=16,
    )
    im2 = ax2.scatter(
        cc_combined_gdf.dem_mean,
        cc_combined_gdf.slope_mean
        s=0.5,
        c=density_velmedian_epsg4326_gdf.LDS_density,
        norm=matplotlib.colors.LogNorm(
            vmin=np.nanpercentile(density_velmedian_epsg4326_gdf.LDS_density, 2),
            vmax=1,
        ),
        cmap="magma",
    )
    ax2.set_xlabel('Landslide mean elevation (m)', fontsize=12)
    # ax2.set_ylabel('Landslide mean slope (degree)', fontsize=12)
    ax2.grid()
    ax2.set_title(
        "Elevation-Slope-Density for radius=%d km (n=%s)"
        % (radius / 1000, f"{len(cc_combined_epsg4326):,}"),
        fontsize=16,
    )
    h = plt.colorbar(im2, ax=ax2, shrink=0.7, orientation="horizontal")
    h.set_label("Landslide Density (#/%.1f km2)" % ((np.pi * radius**2) / 1e6))
    fig.savefig(
        os.path.join(
            gpkg_dir, "CC_landslide_elevation_slope_medianvelocity_density_radius%d.png" % radius
        ),
        dpi=300,
    )


def plot_map_lds_areas(gdf_epsg4326, radius):
    points = np.c_[gdf_epsg4326.centroid.x.values, gdf_epsg4326.centroid.y.values]
    fig, (ax1, ax2) = plt.subplots(
        nrows=1, ncols=2, figsize=(16, 9), dpi=300, layout="constrained"
    )
    im1 = ax1.scatter(
        points[:, 0],
        points[:, 1],
        s=0.5,
        c=gdf_epsg4326["LDS_area_fraction"],
        norm=matplotlib.colors.LogNorm(
            vmin=np.min(gdf_epsg4326["LDS_area_fraction"]),
            vmax=1,
        ),
        cmap="viridis",
    )
    h = plt.colorbar(im1, ax=ax1, shrink=0.7, orientation="horizontal")
    h.set_label(
        "Landslide Area fraction (summed LDS area/%.1f km2)"
        % ((np.pi * radius**2) / 1e6)
    )
    ax1.grid()
    ax1.set_title(
        "Landslide Area fraction for radius=%d km (n=%s)"
        % (radius / 1000, f"{len(cc_combined_epsg4326):,}"),
        fontsize=16,
    )
    im2 = ax2.scatter(
        points[:, 0],
        points[:, 1],
        s=0.5,
        c=gdf_epsg4326["LDS_area_median"] / 1e6,
        norm=matplotlib.colors.LogNorm(
            vmin=np.percentile(gdf_epsg4326["LDS_area_median"], 2) / 1e6,
            vmax=np.percentile(gdf_epsg4326["LDS_area_median"], 98) / 1e6,
        ),
        cmap="magma",
    )
    ax2.grid()
    ax2.set_title(
        "Landslide Median Area (n=%s)" % (f"{len(cc_combined_epsg4326):,}"),
        fontsize=16,
    )
    h = plt.colorbar(im2, ax=ax2, shrink=0.7, orientation="horizontal")
    h.set_label("Landslide Median Area (km2)")
    plt.rc("xtick", labelsize=12)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=12)  # fontsize of the tick labels
    fig.savefig(
        os.path.join(gpkg_dir, "CC_landslide_area_fraction_radius%d.png" % radius),
        dpi=300,
    )


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    gpkg_dir = "/home/bodo/Dropbox/Argentina/CAndes_LDS/Landsat_LDS/"
    gpkg_fname = "P???R???/CORR_os05_bs91_sr06_ms05_corr*_B_median_velocity_magnitude_my_cc1e4m2.gpkg"
    gpkg_fname = os.path.join(gpkg_dir, gpkg_fname)
    gpkg_fname_list = glob.glob(gpkg_fname)
    gpkg_fname_list.sort()
    logging.info("Found %d gpkg files." % len(gpkg_fname_list))

    gpkg_clip_dir = "/home/bodo/Dropbox/Argentina/CAndes_LDS/LDS_extents/"
    gpkg_clip_fname = "P???R???_matching_extent.geojson"
    gpkg_clip_fname = os.path.join(gpkg_clip_dir, gpkg_clip_fname)
    gpkg_clip_fname_list = glob.glob(gpkg_clip_fname)
    gpkg_clip_fname_list.sort()
    logging.info("Found %d clip files." % len(gpkg_clip_fname_list))

    logging.info("Reading gpkg files and clipping with matching extent")
    data_crs = "epsg:32619"
    cc_combined_gdf = []
    for i in tqdm.tqdm(range(len(gpkg_fname_list))):
        cfname = gpkg_fname_list[i]
        cgpd = gpd.GeoDataFrame(gpd.read_file(cfname).to_crs(data_crs))
        # better to implement name check of polygon file here
        clip_cfname = gpkg_clip_fname_list[i]
        cclip = gpd.GeoDataFrame(gpd.read_file(clip_cfname).to_crs(data_crs))
        if cgpd.crs != cclip.crs:
            cclip = cclip.to_crs(points_gdf.crs)
        clipped_cgpd = gpd.clip(cgpd, cclip)
        cc_combined_gdf.append(clipped_cgpd)
    cc_combined_gdf = pd.concat(cc_combined_gdf)

    # this code snippet only reads the gpkg landslide files without clipping
    # logging.info("Reading gpkg files...")
    # data_crs = "epsg:32619"
    # cc_combined_gdf = gpd.GeoDataFrame(
    #     pd.concat(
    #         [gpd.read_file(i).to_crs(data_crs) for i in gpkg_fname_list],
    #         ignore_index=True,
    #     ),
    #     crs=data_crs,
    # )
    cc_combined_gdf.drop(
        columns=[
            "centroid_x",
            "centroid_y",
            "bbox_x1",
            "bbox_x2",
            "bbox_y1",
            "bbox_y2",
            "bbox_x_coord1",
            "bbox_x_coord2",
            "bbox_y_coord1",
            "bbox_y_coord2",
        ],
        inplace=True,
    )
    logging.info("Loaded %s landslides" % f"{len(cc_combined_gdf):,}")
    cc_combined_gdf = cc_combined_gdf[cc_combined_gdf.dem_mean > 500]
    cc_combined_gdf = cc_combined_gdf[cc_combined_gdf.slope_mean > 5]
    logging.info("After filtering: %s landslides" % f"{len(cc_combined_gdf):,}")
    cc_combined_epsg4326 = cc_combined_gdf.to_crs("epsg:4326")

    logging.info("Plot Landslide area and velocity histogram")
    plot_area_velocity_hist()

    # coordinates should be project coordinates, otherwise point distances will need to be weighted
    points = np.c_[cc_combined_gdf.centroid.x.values, cc_combined_gdf.centroid.y.values]
    radius = 5000  # change this to a reasonable radius in m
    densities, counts, vel_median, lds_area_sum, lds_area_median, area_fraction = (
        calculate_point_density(points, radius=radius)
    )
    density_velmedian_pd = pd.DataFrame(
        data=np.c_[densities, vel_median, lds_area_sum, lds_area_median, area_fraction],
        columns=[
            "LDS_density",
            "LDS_vel_median",
            "LDS_area_sum",
            "LDS_area_median",
            "LDS_area_fraction",
        ],
    )
    logging.info("Write Landslide densities to GPKG file")
    density_velmedian_gdf = gpd.GeoDataFrame(
        density_velmedian_pd,
        geometry=gpd.points_from_xy(
            cc_combined_gdf.centroid.x, cc_combined_gdf.centroid.y
        ),
        crs=cc_combined_gdf.crs,
    )
    density_velmedian_gdf_fn = os.path.join(
        gpkg_dir,
        "CC_density_medianvelocity_radius%d_epsg%s.gpkg"
        % (radius, data_crs.split(":")[1]),
    )
    density_velmedian_gdf.to_file(density_velmedian_gdf_fn)

    logging.info("Convert Landslide densities to EPSG 4326 and write to GPKG")
    density_velmedian_epsg4326_gdf_fn = os.path.join(
        gpkg_dir, "CC_density_medianvelocity_radius%d_epsg4326.gpkg" % (radius)
    )
    density_velmedian_epsg4326_gdf = density_velmedian_gdf.to_crs("epsg:4326")
    density_velmedian_epsg4326_gdf.to_file(density_velmedian_epsg4326_gdf_fn)

    logging.info("Plot Density Maps (density, median velocity)")
    plot_map_density_med_velocity(density_velmedian_epsg4326_gdf, radius)

    logging.info("Plot Landslide area fractions")
    plot_map_lds_areas(density_velmedian_epsg4326_gdf, radius)

    logging.info("Plot Density Maps with Elevations (density, median velocity)")
    plot_area_velocity_elevation_hist()

    logging.info('Elevation-Slope-Velocity relation')
    plot_slope_elevation_med_velocity(cc_combined_gdf, density_velmedian_epsg4326_gdf)
