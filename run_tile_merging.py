import numpy as np
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, glob, tqdm
from matplotlib import pyplot as plt

gdal.DontUseExceptions()
osr.DontUseExceptions()


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


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


def read_patch_info_npy(fname):
    npy = np.load(fname)
    return npy.ravel()


def read_tiled_data(tile_files):
    # create large tile that contains full array and then place patches into the merged array
    data_full = np.empty((iheight + pad_height, iwidth + pad_width), dtype=np.float32)
    # data_full.fill(np.nan)
    data_full.fill(-9999)
    steps_dim0 = [tile_size * tiles for tiles in range(dim0)]
    steps_dim1 = [tile_size * tiles for tiles in range(dim1)]
    all_steps_dim0 = np.empty((dim0, dim1), dtype=np.int16)
    all_steps_dim1 = np.empty((dim0, dim1), dtype=np.int16)
    for j in range(len(all_steps_dim0)):
        for k in range(len(all_steps_dim1)):
            all_steps_dim0[j, k] = steps_dim0[j]
            all_steps_dim1[j, k] = steps_dim1[k]

    for i in tqdm.tqdm(range(len(tile_files)), desc="Loading and merging tiles"):
        tilenr = int(
            os.path.basename(tile_files[i]).split("_")[4]
        )  # tilenr from filename
        tile_data = np.load(tile_files[i])

        if all_steps_dim0.ravel()[i] == 0 and all_steps_dim1.ravel()[i] == 0:
            tile_data_clipped = tile_data[
                overlap : patch_size - overlap, overlap : patch_size - overlap
            ]
        elif all_steps_dim0.ravel()[i] == 0 and all_steps_dim1.ravel()[i] > 0:
            tile_data_clipped = tile_data[
                overlap : patch_size - overlap, overlap : patch_size - overlap
            ]
        elif all_steps_dim0.ravel()[i] > 0 and all_steps_dim1.ravel()[i] == 0:
            tile_data_clipped = tile_data[
                0 : patch_size - overlap, overlap : patch_size - overlap
            ]
        else:
            tile_data_clipped = tile_data[
                0 : patch_size - overlap, 0 : patch_size - overlap
            ]

        start_tile_x = all_steps_dim0.ravel()[
            i
        ]  # shape[0] coordinate of where tile is placed into full array
        start_tile_y = all_steps_dim1.ravel()[i]

        data_full[
            start_tile_x : start_tile_x + tile_size,
            start_tile_y : start_tile_y + tile_size,
        ] = tile_data_clipped[0:tile_size, 0:tile_size]

    data_full = data_full[0:iheight, 0:iwidth]
    return data_full


def plot_merged_tiles(udata, vdata, correlationdata, bsdata, png_fn):
    fig, ax = plt.subplots(2, 2, figsize=(16, 9), dpi=300)
    im0 = ax[0, 0].imshow(
        udata, vmin=-search_radius, vmax=search_radius, cmap="seismic"
    )
    h = plt.colorbar(im0, ax=ax[0, 0], orientation="horizontal")
    h.set_label("u")
    ax[0, 0].axis("off")
    im1 = ax[0, 1].imshow(
        vdata, vmin=-search_radius, vmax=search_radius, cmap="seismic"
    )
    h = plt.colorbar(im1, ax=ax[0, 1], orientation="horizontal")
    h.set_label("v")
    ax[0, 1].axis("off")
    im2 = ax[1, 0].imshow(
        correlationdata,
        vmin=np.nanpercentile(correlationdata, 2),
        vmax=np.nanpercentile(correlationdata, 98),
        cmap="viridis",
    )
    h = plt.colorbar(im2, ax=ax[1, 0], orientation="horizontal")
    h.set_label("correlation")
    ax[1, 0].axis("off")
    im3 = ax[1, 1].imshow(
        bsdata,
        vmin=np.nanpercentile(bsdata, 2),
        vmax=np.nanpercentile(bsdata, 98),
        cmap="magma",
    )
    h = plt.colorbar(im3, ax=ax[1, 1], orientation="horizontal")
    h.set_label("block size")
    ax[1, 1].axis("off")
    fig.suptitle("%s" % (png_fn))
    fig.tight_layout()
    fig.savefig(png_fn, dpi=300)
    plt.close()


if __name__ == "__main__":
    dirname = sys.argv[1]
    tileinfo_dirname = sys.argv[2]
    tile_size = sys.argv[3]
    oversampling = sys.argv[4]
    block_size = int(sys.argv[5])
    search_radius = int(sys.argv[6])
    source_geotiff_fn = sys.argv[7]

    # python run_tile_merging.py 231077/20130820_20240420_os01 231077/2130820_os01 8192 1 21 9
    dirname = "231077/20130820_20240420_os02/"
    tileinfo_dirname = "231077/20130820_os02/"
    tile_size = 4096
    oversampling = 2
    block_size = 31
    search_radius = 6
    source_geotiff_fn = ""

    logging.info(
        "Merging tiles for %s with block size: %02d and search radius: %02d"
        % (dirname, block_size, search_radius)
    )
    tileinfo_npyfname = glob.glob(
        os.path.join(
            tileinfo_dirname, "*_tileinfo_%04d_os%02d.npy" % (tile_size, oversampling)
        )
    )[0]

    # tilesize is tile size from tileinfo file, tile_size is value from command line
    (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        dim0,
        dim1,
        dim2,
        overlap,
        tilesize,
    ) = read_patch_info_npy(tileinfo_npyfname)

    # Merge u, v, correlation, block_size
    ufiles = glob.glob(
        os.path.join(
            dirname,
            "*_%04d_os%02d_*_bs%02d_sr%02d_u.npy"
            % (tile_size, oversampling, block_size, search_radius),
        )
    )
    ufiles.sort()
    logging.info(
        "u: Merging %02d tiles for %s with block size: %02d and search radius %02d"
        % (len(ufiles), dirname, block_size, search_radius)
    )
    udata = read_tiled_data(ufiles)
    udata[udata == -9999] = np.nan

    vfiles = glob.glob(
        os.path.join(
            dirname,
            "*_%04d_os%02d_*_bs%02d_sr%02d_v.npy"
            % (tile_size, oversampling, block_size, search_radius),
        )
    )
    vfiles.sort()
    logging.info(
        "v: Merging %02d tiles for %s with block size: %02d and search radius %02d"
        % (len(vfiles), dirname, block_size, search_radius)
    )
    vdata = read_tiled_data(vfiles)
    vdata[vdata == -9999] = np.nan

    correlationfiles = glob.glob(
        os.path.join(
            dirname,
            "*_%04d_os%02d_*_bs%02d_sr%02d_correlation.npy"
            % (tile_size, oversampling, block_size, search_radius),
        )
    )
    correlationfiles.sort()
    logging.info(
        "correlation: Merging %02d tiles for %s with block size: %02d and search radius %02d"
        % (len(correlationfiles), dirname, block_size, search_radius)
    )
    correlationdata = read_tiled_data(correlationfiles)
    correlationdata[correlationdata == -9999] = np.nan

    bsfiles = glob.glob(
        os.path.join(
            dirname,
            "*_%04d_os%02d_*_bs%02d_sr%02d_bs.npy"
            % (tile_size, oversampling, block_size, search_radius),
        )
    )
    bsfiles.sort()
    logging.info(
        "bs: Merging %02d tiles for %s with block size: %02d and search radius %02d"
        % (len(bsfiles), dirname, block_size, search_radius)
    )
    bsdata = read_tiled_data(bsfiles)
    bsdata[bsdata == -9999] = np.nan

    png_fn = dirname + "_merged_tiles.png"
    logging.info("Plotting u, v, correlation, and blocksize data to %s" % (png_fn))
    plot_merged_tiles(udata, vdata, correlationdata, bsdata, png_fn)

    logging.info("Extract geotiff information from %s" % (source_geotiff_fn))
    gt, proj, epsg_code, ys, xs = get_geotiff_info(source_geotiff_fn)

    geotiff_fn = os.path.basename(dirname) + "_u_epsg%s.tif" % (epsg_code)
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(geotiff_fn, udata, int(epsg_code), geotransform=gt, nan_value=np.nan)
    geotiff_fn = os.path.basename(dirname) + "_v_epsg%s.tif" % (epsg_code)
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(geotiff_fn, vdata, int(epsg_code), geotransform=gt, nan_value=np.nan)
    geotiff_fn = os.path.basename(dirname) + "_correlation_epsg%s.tif" % (epsg_code)
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(
        geotiff_fn, correlationdata, int(epsg_code), geotransform=gt, nan_value=np.nan
    )
    geotiff_fn = os.path.basename(dirname) + "_bs_epsg%s.tif" % (epsg_code)
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_geotiff(geotiff_fn, bsdata, int(epsg_code), geotransform=gt, nan_value=np.nan)
