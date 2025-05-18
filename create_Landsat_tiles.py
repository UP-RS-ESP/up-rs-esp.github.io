import numpy as np
import glob, os, tqdm, logging, os, sys
from osgeo import gdal
from matplotlib import pyplot as plt
import matplotlib.ticker as plticker
import matplotlib.cm as cm
import matplotlib.patches as patches
from scipy.ndimage import zoom

# from cupyx.scipy import ndimage

gdal.UseExceptions()


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("float32")
    # make sure that raster is properly pre-processed. Set 0 and -9999 to nan
    Landsat_B8[Landsat_B8 == 0] = np.nan
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj


def patchify_with_overlap(x, tile_size=4096, overlap=32):
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
        :: tile_size + overlap, :: tile_size + overlap
    ]
    return (
        iheight,
        iwidth,
        pad_height,
        pad_width,
        patch_size,
        foo.shape[0],
        foo.shape[1],
        foo.shape[2],
        foo.reshape((foo.shape[0] * foo.shape[1], foo.shape[2], foo.shape[3])),
    )


def plot_patches(x, savepng_tiles_output_file, title, oversampling):
    # plot all patches
    nr_patches = x.shape[0]
    nr_rows = 4
    nr_cols = 4
    nr_of_subplots = nr_rows * nr_cols
    nr_of_pages = int(np.ceil(nr_patches / nr_of_subplots))
    # logging.info("Plotting %d patches on %d page(s)" % (nr_patches, nr_of_pages))
    icounter = 0

    for pagenr in tqdm.tqdm(range(nr_of_pages), desc="Plotting tiled images"):
        if nr_of_pages > 0:
            csavepng_tiles_output_file = savepng_tiles_output_file[
                :-4
            ] + "_os%02d_page%02d.png" % (oversampling, pagenr)
        fig, ax = plt.subplots(nr_rows, nr_cols, figsize=(16, 9), dpi=300)
        plotx, ploty = 0, 0
        if pagenr == 0:
            cimages_id = list(range(0, nr_of_subplots))
        if pagenr > 0:
            cimages_id = list(
                range(nr_of_subplots * pagenr, (nr_of_subplots * (pagenr + 1)))
            )
        for cimage in range(len(cimages_id)):
            if cimage > 0:
                if ploty == nr_cols - 1:
                    ploty = 0
                    plotx = plotx + 1
                else:
                    ploty = ploty + 1
            if icounter >= nr_patches:
                ax[plotx, ploty].axis("off")
                continue
            ax[plotx, ploty].imshow(x[cimage, :, :], cmap="gray")
            ax[plotx, ploty].set_aspect("equal", "box")
            ax[plotx, ploty].set_title(
                "%02d" % (cimage,),
                fontsize=8,
            )
            ax[plotx, ploty].axis("off")
            icounter += 1

        fig.suptitle(
            "Page %d/%d: %s tile (%d x %d pixels with %d pixels overlap) %d x oversampling"
            % (
                pagenr + 1,
                nr_of_pages,
                title,
                tile_size,
                tile_size,
                overlap,
                oversampling,
            )
        )
        fig.tight_layout()
        fig.savefig(csavepng_tiles_output_file, dpi=300)
        plt.close()


def write_patches_npy(x, dirname, name, oversampling):
    # logging.info("Save %02d patches to npy files" % x.shape[0])
    for i in range(x.shape[0]):
        cpatch = x[i, :, :]
        fname = os.path.join(dirname, name + "_os%02d_%02d.npy" % (oversampling, i))
        np.save(fname, cpatch)


def write_patch_info_npy(x, dirname, name, oversampling):
    fname = os.path.join(dirname, name + "_tileinfo_os%02d.npy" % (oversampling))
    np.save(fname, x)


if __name__ == "__main__":
    # python create_Landsat_tiles.py <Landsat_dir> <tile_size> <overlap> <oversampling>
    basedir = sys.argv[1]  # "/raid2-gpu2/bodo/Landsat-test/"
    tile_size = int(sys.argv[2])  # 8192
    overlap = int(sys.argv[3])  # 32
    oversampling = int(sys.argv[4])  # 1, 2, 4-times oversampling
    fnames = glob.glob(os.path.join(basedir, "*_B8.TIF"))
    # assume that all TIF files in that directory are correlated against each other
    # basedir = "/raid2-gpu2/bodo/Landsat-test/"
    # tile_size = 8192
    # overlap = 32
    # oversampling = 2
    # fnames = glob.glob(os.path.join(basedir, "*_B8.TIF"))

    # Store GeoTransform and Projection information
    Landsat_gt = []
    Landsat_proj = []

    for i in range(len(fnames)):
        fname = fnames[i]
        name = os.path.basename(fname).split(".")[0]
        dirname = os.path.dirname(fname)
        name_year = name.split("_")[3] + "_os%02d" % oversampling
        name_rowcol = name.split("_")[2]
        logging.info("%d/%d: %s" % (i + 1, len(fnames), name))

        if not os.path.exists(os.path.join(dirname, name_rowcol)):
            os.mkdir(os.path.join(dirname, name_rowcol))
        if not os.path.exists(os.path.join(dirname, name_rowcol, name_year)):
            os.mkdir(os.path.join(dirname, name_rowcol, name_year))

        name_year_dir = os.path.join(dirname, name_rowcol, name_year)

        Landsat_B8, Landsat_ds_gt, Landsat_ds_proj = load_Landsat_tif(fname)
        Landsat_gt.append(Landsat_ds_gt)
        Landsat_proj.append(Landsat_ds_proj)
        if oversampling > 1:
            logging.info(
                "%d/%d: Oversampling with factor %d"
                % (i + 1, len(fnames), oversampling)
            )
            Landsat_B8 = zoom(
                Landsat_B8, oversampling, mode="reflect", order=2, prefilter=False
            )
            # perform resampling on the CUDA - not working for large images
            # Landsat_B8 = (
            #    ndimage.zoom(
            #        cp.array(Landsat_B8, dtype=cp.float32),
            #        oversampling,
            #        prefilter=False,
            #        order=2,
            #        mode="reflect",
            #        output=cp.float32,
            #    )
            #    .get()
            #    .astype(np.float32)
            # )

        logging.info("%d/%d: Patchify array" % (i + 1, len(fnames)))
        (
            iheight,
            iwidth,
            pad_height,
            pad_width,
            patch_size,
            dim0,
            dim1,
            dim2,
            Landsat_B8_patches,
        ) = patchify_with_overlap(Landsat_B8, tile_size=tile_size, overlap=overlap)
        logging.info("%d/%d: Plot patches" % (i + 1, len(fnames)))
        plot_patches(
            Landsat_B8_patches,
            os.path.join(dirname, name_rowcol, name),
            name_year,
            oversampling,
        )

        logging.info(
            "%d/%d: Save %d patches to npy"
            % (i + 1, len(fnames), Landsat_B8_patches.shape[0])
        )
        write_patches_npy(
            Landsat_B8_patches,
            dirname=name_year_dir,
            name=name,
            oversampling=oversampling,
        )

        logging.info("%d/%d: Save tile information to npy" % (i + 1, len(fnames)))
        write_patch_info_npy(
            np.c_[
                iheight,
                iwidth,
                pad_height,
                pad_width,
                patch_size,
                dim0,
                dim1,
                dim2,
                overlap,
            ],
            dirname=name_year_dir,
            name=name,
            oversampling=oversampling,
        )
