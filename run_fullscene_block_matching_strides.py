import numpy as np
import numba as nb
from numba import cuda
from math import sqrt
from osgeo import gdal
from osgeo import osr
import os, logging, time, sys, tqdm
import matplotlib.pyplot as plt
import scipy.optimize
from numpy.lib.stride_tricks import sliding_window_view


gdal.UseExceptions()

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def write_patch_correlation_npy(u, v, block_sizes, correlation, dirname, fname):
    fname_u = os.path.join(dirname, fname + "_u.npy")
    np.save(fname_u, u)
    fname_v = os.path.join(dirname, fname + "_v.npy")
    np.save(fname_v, v)
    fname_bs = os.path.join(dirname, fname + "_bs.npy")
    np.save(fname_bs, block_sizes)
    fname_c = os.path.join(dirname, fname + "_correlation.npy")
    np.save(fname_c, correlation)


# Verify that cuda is available
cuda_status = cuda.detect()
if not cuda_status:
    logging.info("No CUDA found. Stopping.")
    sys.exit(-1)

def load_mask_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint8")
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, int(epsg)


def load_Landsat_tif(fname):
    Landsat_ds = gdal.Open(fname)
    Landsat_ds_gt = Landsat_ds.GetGeoTransform()
    Landsat_ds_proj = Landsat_ds.GetProjection()
    epsg = osr.SpatialReference(wkt=Landsat_ds_proj).GetAttrValue("AUTHORITY", 1)
    # Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray()).astype("uint16")
    Landsat_B8 = np.array(Landsat_ds.GetRasterBand(1).ReadAsArray(xoff=2000, yoff=2000, win_xsize=500, win_ysize=500)).astype("uint16")
    Landsat_ds = None
    return Landsat_B8, Landsat_ds_gt, Landsat_ds_proj, int(epsg)


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


def save_mask_geotiff(geotiff_fn, array, epsg_code, geotransform):
    # mask value is 1 - all values with 1 are masked out (True)
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
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
    )
    outRaster.SetGeoTransform(geotransform)
    outRaster.SetProjection(srs.ExportToProj4())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.FlushCache()
    outband.ComputeStatistics(0)
    outband.FlushCache()
    del outband, outRaster, driver


def save_c_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=0):
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
        gdal.GDT_Byte,  # GDT_Byte is an 8 bit unsigned integer
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
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


def save_uv_geotiff(geotiff_fn, array, epsg_code, geotransform, nan_value=-128):
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
        gdal.GDT_Int8,
        options=["COMPRESS=DEFLATE", "ZLEVEL=7", "PREDICTOR=2"],
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


def save_all_geotiff(tifdirname):
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_u.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(
        geotiff_fn,
        u,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_v.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_uv_geotiff(geotiff_fn, v, int(epsg_code), geotransform=Landsat_1_ds_gt)
    # geotiff_fn = os.path.join(
    #     tifdirname,
    #     os.path.basename(dirname)
    #     + "_bs%02d_sr%02d_ms%02d_blocksizes.tif"
    #     % (
    #         block_size,
    #         search_radius,
    #         matching_step,
    #     ),
    # )
    # logging.info("Save geotiff to %s" % (geotiff_fn))
    # save_geotiff(
    #     geotiff_fn,
    #     block_sizes,
    #     int(epsg_code),
    #     geotransform=Landsat_1_ds_gt,
    # )
    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_correlation.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_c_geotiff(
        geotiff_fn,
        correlation,
        int(epsg_code),
        geotransform=Landsat_1_ds_gt,
    )

def Gaussian2D(xy, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    x, y = xy
    xo = float(xo)
    yo = float(yo)    
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)
    g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo) 
                            + c*((y-yo)**2)))
    return g.ravel()


def pearsonr_2D_array(x, y):
    """computes pearson correlation coefficient
       where x is a 1D and y a 2D array"""
    rho = np.empty( (x.shape[0], y.shape[1]), dtype=np.float32)
    rho.fill(np.nan)
    for i in tqdm.tqdm(range(x.shape[0])):
        upper = np.sum((x[i,:] - np.mean(x[i,:])) * (y[i,:] - np.mean(y[i,:], axis=1)[:,None]), axis=1)
        lower = np.sqrt(np.sum(np.power(x[i,:] - np.mean(x[i,:]), 2)) * np.sum(np.power(y[i,:] - np.mean(y[i,:], axis=1)[:,None], 2), axis=1))
        rho[i] = upper / lower
    return rho


@nb.njit(parallel=True) 
def pearsonr_2D_numba(x, y):
    """computes pearson correlation coefficient
       where x is a 1D and y a 2D array"""
    rho = np.empty( (x.shape[0], y.shape[1]), dtype=np.float32)
    rho.fill(np.nan)
    for i in nb.prange(x.shape[0]):
        rho[i]=np.corrcoef(x[i,:], y[i,:,:])[1:,0]
    return rho

def pearsonr_2D(x, y):
    """computes pearson correlation coefficient
       where x is a 1D and y a 2D array"""
    upper = np.sum((x - np.mean(x)) * (y - np.mean(y, axis=1)[:,None]), axis=1)
    lower = np.sqrt(np.sum(np.power(x - np.mean(x), 2)) * np.sum(np.power(y - np.mean(y, axis=1)[:,None], 2), axis=1))
    rho = upper / lower
    return rho


    
def plot_cc_fits(corrcoef_img, corrcoef_p2_img, corrcoef_G2D_img, 
                 CC_argmax_x, CC_argmax_y, Zi_argmax_x, Zi_argmax_y, 
                 G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, p2_rmse, p2_iqr, G2D_rmse, G2D_iqr, fig_title, pngfn):
    fig, ax = plt.subplots(
        nrows=1, ncols=3, figsize=(16, 8), dpi=300, layout="constrained"
    )
    im0 = ax[0].imshow(corrcoef_img, interpolation='nearest', extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    ax[0].plot(CC_argmax_x, CC_argmax_y, 'k+', ms=5, label='max. value from orig.matrix')
    ax[0].plot(Zi_argmax_x, Zi_argmax_y, 'o', color='gray', ms=5, label='2nd order polynomial')
    ax[0].plot(G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, 'o', color='white', ms=5, label='2D Gaussian fit')
    ax[0].get_xaxis().set_ticks([])
    ax[0].get_yaxis().set_ticks([])
    ax[0].set_title('Original CC (%d x %d)'%(corrcoef_img.shape[0], corrcoef_img.shape[1]) )
    im1 = ax[1].imshow(corrcoef_p2_img, interpolation='nearest', extent=[Xmin_fine, Xmax_fine, Ymin_fine, Ymax_fine],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    ax[1].plot(CC_argmax_x, CC_argmax_y, 'k+', ms=5, label='max. value from orig.matrix')
    ax[1].plot(Zi_argmax_x, Zi_argmax_y, 'o', color='gray', ms=5, label='2nd order polynomial')
    ax[1].plot(G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, 'o', color='white', ms=5, label='2D Gaussian fit')
    ax[1].get_xaxis().set_ticks([])
    ax[1].get_yaxis().set_ticks([])
    ax[1].set_title('2nd order polynomial CC RMSE: %2.3f, IQR: %2.3f (%d x %d)'%(p2_rmse, p2_iqr, corrcoef_p2_img.shape[0], corrcoef_p2_img.shape[1]) )
    im2 = ax[2].imshow(
        corrcoef_G2D_img, interpolation='nearest', extent=[Xmin_fine, Xmax_fine, Ymin_fine, Ymax_fine],
        vmin=np.nanpercentile(corrcoef_img, 2),
        vmax=np.nanpercentile(corrcoef_img, 98),
        cmap="magma",
    )
    h = plt.colorbar(im2, ax=ax, orientation="horizontal", shrink=0.8)
    h.set_label("Pearson Correlation Coefficient", fontsize=14)
    ax[2].plot(CC_argmax_x, CC_argmax_y, 'k+', ms=5, label='max. value from orig.matrix')
    ax[2].plot(Zi_argmax_x, Zi_argmax_y, 'o', color='gray', ms=5, label='2nd order polynomial')
    ax[2].plot(G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, 'o', color='white', ms=5, label='2D Gaussian fit')
    ax[2].get_xaxis().set_ticks([])
    ax[2].get_yaxis().set_ticks([])
    ax[2].set_title('2D Gaussian CC RMSE: %2.3f, IQR: %2.3f (%d x %d)'%(G2D_rmse, G2D_iqr, corrcoef_G2D_img.shape[0], corrcoef_G2D_img.shape[1]))
    ax[2].legend()
    fig.suptitle("%s" % (fig_title), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()


def plot_cc_patch(ref_img, sec_img, corrcoef_img, CC_argmax_x, CC_argmax_y, Zi_argmax_x, Zi_argmax_y, G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, fig_title, pngfn):
    fig, ax = plt.subplots(
        nrows=1, ncols=3, figsize=(16, 8), dpi=300, layout="constrained"
    )
    im0 = ax[0].imshow(ref_img,
        vmin=np.nanpercentile(ref_img, 2),
        vmax=np.nanpercentile(ref_img, 98),
        cmap="gray",
    )
    ax[0].get_xaxis().set_ticks([])
    ax[0].get_yaxis().set_ticks([])
    ax[0].set_title('Reference patch')
    im1 = ax[1].imshow(sec_img,
        vmin=np.nanpercentile(ref_img, 2),
        vmax=np.nanpercentile(ref_img, 98),
        cmap="gray",
    )
    ax[1].get_xaxis().set_ticks([])
    ax[1].get_yaxis().set_ticks([])
    ax[1].set_title('Secondary patch')
    h = plt.colorbar(im1, ax=ax[0:2], orientation="horizontal", shrink=0.8)
    h.set_label("Landsat Grayscale", fontsize=14)
    # extent: floats (left, right, bottom, top)
    im2 = ax[2].imshow(
        corrcoef_img, interpolation='nearest', extent=[Xmin, Xmax, Ymin, Ymax],
        vmin=0,
        vmax=1,
        cmap="magma",
    )
    h = plt.colorbar(im2, ax=ax[2], orientation="horizontal", shrink=0.8)
    h.set_label("Pearson Correlation Coefficient", fontsize=14)
    ax[2].plot(CC_argmax_x, CC_argmax_y, 'k+', ms=5, label='max. value from orig.matrix')
    ax[2].plot(Zi_argmax_x, Zi_argmax_y, 'o', color='gray', ms=5, label='2nd order polynomial')
    ax[2].plot(G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, 'o', color='white', ms=5, label='Gaussian2D')
    ax[2].get_xaxis().set_ticks([])
    ax[2].get_yaxis().set_ticks([])
    ax[2].set_title('Pearson Correlation Coefficient')
    ax[2].legend()
    fig.suptitle("%s" % (fig_title), fontsize=16)
    fig.savefig(pngfn, dpi=300)
    plt.close()

def fit_poly2D_ar(coords, corrcoef_ar, coords_fine):
    #fitting second order polynomial
    A = np.c_[
        np.ones(coords.shape[0]),
        coords[:, :2],
        np.prod(coords[:, :2], axis=1),
        coords[:, :2] ** 2,
    ]
    Z, _, _, _ = np.linalg.lstsq(A, corrcoef_ar.T, rcond=None)
    Zi = ( Z[0,:] + Z[1,:] * coords[:,0, None] + Z[2,:] * coords[:,1, None] + 
            Z[3,:] * np.prod(coords[:,np.newaxis], axis=2) + 
            Z[4,:] * coords[:,0, None]**2 + 
            Z[5,:] * coords[:,1,None]**2 )
    dz_p2 = corrcoef_ar.T - Zi
    p2_rmse = np.float32(np.sqrt(np.mean(np.square(dz_p2), axis=0)))
    p2_iqr = np.float32(
        np.percentile(dz_p2, 75, axis=0) - np.percentile(dz_p2, 25, axis=0)
    )
    # create fine mesh for evaluating function
    Zi_fine = ( Z[0,:] + Z[1,:] * coords_fine[:,0, None] + Z[2,:] * coords_fine[:,1, None] + 
            Z[3,:] * np.prod(coords_fine[:,np.newaxis], axis=2) + 
            Z[4,:] * coords_fine[:,0, None]**2 + 
            Z[5,:] * coords_fine[:,1,None]**2 )
    Zi_argmax = np.argmax(Zi_fine, axis=0)
    Zi_argmax_x = sr_coordx_fine[Zi_argmax]
    Zi_argmax_y = sr_coordy_fine[Zi_argmax]
    return p2_rmse, p2_iqr, Zi_fine, Zi_argmax_x, Zi_argmax_y


def fit_poly2D(coords, corrcoef_ar, coords_fine):
    #fitting second order polynomial
    A = np.c_[
        np.ones(coords.shape[0]),
        coords[:, :2],
        np.prod(coords[:, :2], axis=1),
        coords[:, :2] ** 2,
    ]
    Z, _, _, _ = np.linalg.lstsq(A, corrcoef_ar, rcond=None)
    Zi = ( Z[0] + Z[1] * coords[:,0] + Z[2] * coords[:,1] + 
            Z[3] * np.prod(coords, axis=1) + 
            Z[4] * coords[:,0]**2 + 
            Z[5] * coords[:,1]**2 )
    dz_p2 = corrcoef_ar - Zi.reshape(corrcoef_ar.shape)
    p2_rmse = np.float32(np.sqrt(np.mean(np.square(dz_p2))))
    p2_iqr = np.float32(
        np.percentile(dz_p2, 75) - np.percentile(dz_p2, 25)
    )
    # create fine mesh for evaluating function
    Zi_fine = ( Z[0] + Z[1] * coords_fine[:,0] + Z[2] * coords_fine[:,1] + 
            Z[3] * np.prod(coords_fine, axis=1) + 
            Z[4] * coords_fine[:,0]**2 + 
            Z[5] * coords_fine[:,1]**2 )
    Zi_argmax = np.argmax(Zi_fine)
    Zi_argmax_x = sr_coordx_fine[Zi_argmax]
    Zi_argmax_y = sr_coordy_fine[Zi_argmax]
    return p2_rmse, p2_iqr, Zi_fine.reshape((int(np.sqrt(sr_coordx_fine.shape[0])), int(np.sqrt(sr_coordy_fine.shape[0]))) ), Zi_argmax_x, Zi_argmax_y


def fit_Gaussian2D(coords, corrcoef_ar, coords_fine):
    # fit 2D gaussian
    initial_guess = (1,CC_argmax_x,CC_argmax_y,20,20,0,0)
    param, _ = scipy.optimize.curve_fit(
        f=Gaussian2D,
        xdata=coords.T,
        ydata=corrcoef_ar,
        p0=initial_guess
    )
    G2D_fit = Gaussian2D(coords.T, *param).reshape( (search_radius*2+1, search_radius*2+1) )
    dz_G2D = corrcoef_ar - G2D_fit.reshape(corrcoef_ar.shape)
    G2D_rmse = np.float32(np.sqrt(np.mean(np.square(dz_G2D))))
    G2D_iqr = np.float32(
        np.percentile(dz_G2D, 75) - np.percentile(dz_G2D, 25)
    )
    G2D_fit_fine = Gaussian2D(coords_fine.T, *param)
    G2D_fit_fine_argmax = np.argmax(G2D_fit_fine)
    G2D_fit_fine_argmax_x = sr_coordx_fine[G2D_fit_fine_argmax]
    G2D_fit_fine_argmax_y = sr_coordy_fine[G2D_fit_fine_argmax]
    return G2D_rmse, G2D_iqr, G2D_fit_fine.reshape( 
            (int(np.sqrt(sr_coordx_fine.shape[0])), int(np.sqrt(sr_coordy_fine.shape[0]))) ), G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y


if __name__ == "__main__":
    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching.py \
    #   /work/bookhage/Landsat/P231R078/corr_dates_sd1_cc20 \
    #   /work/bookhage/Landsat/P231R078/run_block_matching_231078_os05_bs121_sr08_ms05.bash \
    #   231078 121 8 5 5 2 \
    #   /work/bookhage/Landsat/P231R078/CORR_os05_bs121_sr08_ms05
    fname1 = sys.argv[1]
    fname2 = sys.argv[2]
    block_size = int(sys.argv[3])
    search_radius = int(sys.argv[4])
    oversampling = int(sys.argv[5])
    matching_step = int(sys.argv[6])
    cudadevice = int(sys.argv[7])
    tifdirname = sys.argv[8]
    nthreads_exp = 9

    fname1="/raid2-gpu2/bodo/LANDSAT/P231R076/CROP/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF"
    fname2="/raid2-gpu2/bodo/LANDSAT/P231R076/CROP/LC08_L1TP_231076_20230715_20230724_02_T1_B8.TIF"
    # fname1 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC08_L1TP_231076_20130601_20200913_02_T1_B8.TIF" 
    # fname2 = "/work/bookhage/Landsat/P231R076/CROP_os05/LC09_L1TP_231076_20240725_20240725_02_T1_B8.TIF"
    block_size = 121
    search_radius = 4
    cudadevice = 0
    oversampling = 5
    matching_step = 1
    tifdirname ='/work/bookhage/Landsat/P231R076/CORR_os05_bs121_sr09_ms01'

    cuda.select_device(cudadevice)
    logging.info("Using CUDA Device %d" % cudadevice)
    logging.info("Loading Landsat TIFs: %s and %s" % (fname1, fname2))
    start0 = time.time()
    Landsat_B8_1, Landsat_1_ds_gt, Landsat_1_ds_proj, epsg_code = load_Landsat_tif(
        fname1
    )
    Landsat_B8_2, Landsat_2_ds_gt, Landsat_2_ds_proj, epsg_code = load_Landsat_tif(
        fname2
    )
    end = time.time()
    length_s = end - start0
    logging.info("Loading Landsat data took %d seconds or %2.2f minutes" % (length_s, length_s / 60))
    if Landsat_B8_1.shape != Landsat_B8_2.shape:
        raise ValueError("img1 and img2 must have the same shape")
    if Landsat_B8_1.ndim != 2:
        raise ValueError("Only 2D arrays supported")

    year_name1 = os.path.basename(fname1).split("_")[3]
    year_name2 = os.path.basename(fname2).split("_")[3]
    fname = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d" % (
        year_name1,
        year_name2,
        oversampling,
        block_size,
        search_radius,
        matching_step,
    )
    dirname = "%s_%s_os%02d" % (year_name1, year_name2, oversampling)
    geotiff_fn_u = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_u.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    geotiff_fn_v = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_v.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    geotiff_fn_c = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_c.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )

    half_block_size = block_size / 2
    R = int(search_radius)
    hbs = int(half_block_size)
    bs = 2 * hbs + 1
    H, W = Landsat_B8_1.shape
    # Pad so that every pixel center is valid:
    pad_mode = "reflect"
    img1p = np.pad(Landsat_B8_1, ((hbs, hbs), (hbs, hbs)), mode=pad_mode)
    img2p = np.pad(Landsat_B8_2, ((hbs + R, hbs + R), (hbs + R, hbs + R)), mode=pad_mode)
    # Patches centered at every original pixel
    ref_patches = sliding_window_view(img1p, (bs, bs))
    # All candidate patches in img2 (including extra R border)
    cand_patches = sliding_window_view(img2p, (bs, bs))
    # For each (y, x), collect candidate patches in a (2R+1)x(2R+1) window
    disp_view = sliding_window_view(
        cand_patches, window_shape=(2 * R + 1, 2 * R + 1), axis=(0, 1)
    )
    sr_coordx, sr_coordy = np.meshgrid(
        np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
        np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]),
    )
    sr_coordx = sr_coordx.ravel()
    sr_coordy = sr_coordy.ravel()
    coords = np.c_[sr_coordx, sr_coordy]

    coord_upsampling_factor = 10
    sr_coordx_fine, sr_coordy_fine = np.meshgrid(
        np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
        np.arange(0, ((search_radius * 2) + 1) * Landsat_1_ds_gt[1], Landsat_1_ds_gt[1]/coord_upsampling_factor),
    )
    sr_coordx_fine = sr_coordx_fine.ravel()
    sr_coordy_fine = sr_coordy_fine.ravel()
    Xmin_fine = np.min(sr_coordx_fine)
    Xmax_fine = np.max(sr_coordx_fine)
    Ymin_fine = np.min(sr_coordy_fine)
    Ymax_fine = np.max(sr_coordy_fine)
    coords_fine = np.c_[sr_coordx_fine, sr_coordy_fine]

    # calculate corr. coef. for every pixel in search radius:
    logging.info("Creating strides copy")
    start0 = time.time()
    sec = np.float32(disp_view[:, :, :, :, :, :].reshape(disp_view.shape[2]*disp_view.shape[3],disp_view.shape[4]*disp_view.shape[5],disp_view.shape[0]*disp_view.shape[1]).T)
    end = time.time()
    length_s = end - start0
    logging.info("took %d seconds or %2.2f minutes" % (length_s, length_s / 60))
    # ref = np.repeat(np.atleast_2d(ref_patches[i, j, :,:].ravel()), sec.shape[0], axis=0)
    # using custom function to calculate pearson Corr. from 2D vs 1D array:
    logging.info("Calculating Pearson CC")
    start0 = time.time()
    corrcoef_ar = pearsonr_2D_numba(np.float32(ref_patches[:, :, :,:].reshape(ref_patches.shape[0]*ref_patches.shape[1], ref_patches.shape[2]*ref_patches.shape[3])), sec)
    end = time.time()
    length_s = end - start0
    logging.info("took %d seconds or %2.2f minutes" % (length_s, length_s / 60))
    # import cupy as cp
    # cp.asnumpy(cp.corrcoef(x, dtype=cp.float32))
    CC_argmax = np.argmax(corrcoef_ar, axis=1)
    CC_argmax_x = sr_coordx[CC_argmax]
    CC_argmax_y = sr_coordy[CC_argmax]
    # CC_argmax_idx_x, CC_argmax_idx_y = np.unravel_index(CC_argmax, corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5]).shape)
    Xmin = np.min(sr_coordx)
    Xmax = np.max(sr_coordx)
    Ymin = np.min(sr_coordy)
    Ymax = np.max(sr_coordy)

    logging.info("Fitting 2D polynomial function")
    start0 = time.time()
    p2_rmse, p2_iqr, p2_Zi, Zi_argmax_x, Zi_argmax_y = fit_poly2D_ar(coords, corrcoef_ar, coords_fine)
    # G2D_rmse, G2D_iqr, G2D_Zi, G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y = fit_Gaussian2D(coords, corrcoef_ar, coords_fine)
    end = time.time()
    length_s = end - start0
    logging.info("took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

    corrcoef_img = corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5])
    pngfn = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d_x%05d_y%05d_CC_comparison.png" % (
        year_name1,
        year_name2,
        oversampling,
        block_size,
        search_radius,
        matching_step,i, j
    )
    fig_title = "%s-%s: Cor. Coef. comparison (px=%d, %d, bs=%d, sr=%d)" % (year_name1, year_name2, i, j, ref_img.shape[0], search_radius)
    plot_tile_cc_fits(corrcoef_img, p2_Zi, 
                G2D_Zi, CC_argmax_x, CC_argmax_y, Zi_argmax_x, Zi_argmax_y, 
                G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y, p2_rmse, p2_iqr, G2D_rmse, G2D_iqr, fig_title, pngfn)

    pngfn = "%s_%s_os%02d_bs%02d_sr%02d_ms%02d_x%05d_y%05d" % (
        year_name1,
        year_name2,
        oversampling,
        block_size,
        search_radius,
        matching_step,i, j
    )
    fig_title = "%s-%s: CC (n=%dx%d)" % (year_name1, year_name2, ref_img.shape[0], ref_img.shape[1])
    plot_cc_patch(ref_img, sec_img, corrcoef_ar.reshape(disp_view.shape[4], disp_view.shape[5]), 
                CC_argmax_x, CC_argmax_y, Zi_argmax_x, Zi_argmax_y, G2D_fit_fine_argmax_x, G2D_fit_fine_argmax_y,  fig_title, pngfn)



                              



    corrcoef_ar = np.corrcoef(disp_view[2000,2000,:,:,0,0].ravel(), ref_patches[2000,2000, :,:].ravel().repeat(10)
np.repeat(np.atleast_2d(ref_patches[2000,2000, :,:].ravel()), 10, axis=0)
    cost_ar = np.abs(disp_view[2000:2005,2000:2005,:,:,:,:] - ref_patches[2000:2005,2000:2005, :,:,None, None])
    corr = cost_ar[0,0,0,0,:,:]
    cost = np.abs(disp_view[0:100,0:100,:,:,:,:] - ref_patches[0:100,0:100, :,:,None, None]).mean(axis=(2,3))

    # argmin over displacement grid -> best (dy, dx) for each pixel
    idx = cost.reshape(H, W, -1).argmin(axis=-1)
    dy_idx, dx_idx = np.divmod(idx, 2 * R + 1)
    dy = dy_idx - R
    dx = dx_idx - R

    best_cost = cost[np.arange(H)[:, None], np.arange(W)[None, :], dy_idx, dx_idx]



    # fname='/work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc30_B_median_velocity_magnitude_my_cc1e4m2_bbox_filtered_buffered45m_mask_os05.tif'
    # Landsat_mask, Landsat_mask_ds_gt, Landsat_mask_ds_proj, epsg_code = load_mask_tif(fname)
    # Landsat_mask_exists = True

                              

    if (
        os.path.exists(geotiff_fn_u)
        and os.path.exists(geotiff_fn_v)
        and os.path.exists(geotiff_fn_c)
    ):
        logging.info(
            "Files exists: %s, %s, %s" % (geotiff_fn_u, geotiff_fn_v, geotiff_fn_c)
        )
        logging.info("exit")
        exit()

    if not os.path.exists(tifdirname):
        os.mkdir(tifdirname)

    # if not os.path.exists(dirname):
    #     os.mkdir(dirname)

    # logging.info("Extract geotiff information from %s" % (fname1))
    # gt, proj, epsg_code, ys, xs = get_geotiff_info(fname1)

    if matching_step != 1:
        logging.info("Masking skip steps with matching step of %02d" % matching_step)
        # apply skip stepsize
        # find center point: matching_step = 3, one step in and then in 3 steps
        Landsat_B8_mask = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        if matching_step == 3:
            Landsat_B8_mask[1::matching_step, 1::matching_step] = 0
        elif matching_step == 5:
            Landsat_B8_mask[2::matching_step, 2::matching_step] = 0
        elif matching_step == 7:
            Landsat_B8_mask[3::matching_step, 3::matching_step] = 0
        elif matching_step == 9:
            Landsat_B8_mask[4::matching_step, 4::matching_step] = 0

        # make sure to mask out nan area surrounding Landsat image
        Landsat_B8_mask[Landsat_B8_1 == 0] = 1
        nr_nan_pixels1 = len(np.where(Landsat_B8_mask == 1)[0])
        logging.info(
            "Masked %s nan pixels (%2.1f %%)"
            % (
                f"{nr_nan_pixels1:,}",
                nr_nan_pixels1 / (Landsat_B8_1.shape[0] * Landsat_B8_1.shape[1]) * 100,
            )
        )
    elif matching_step == 1:
        logging.info("Creating mask for nan areas")
        Landsat_B8_mask = np.ones(Landsat_B8_1.shape, dtype=np.bool_)
        # all areas that not 0 (above 0) are set to 0 in the mask - these are processed
        # all values with 1 are masked out
        # we first set all values from the border to 1
        if Landsat_mask_exists == False:
            Landsat_B8_mask[Landsat_B8_1 != 0] = 0
        elif Landsat_mask_exists == True:
            # next, we set all bbox areas from mask file to 0 (they will be processed)
            Landsat_B8_mask[Landsat_mask == 1] = 0
        nr_nan_pixels1 = np.count_nonzero(Landsat_B8_mask == 1)
        logging.info(
            "Masked %s nan pixels (%2.1f %%)"
            % (
                f"{nr_nan_pixels1:,}",
                nr_nan_pixels1 / (Landsat_B8_1.shape[0] * Landsat_B8_1.shape[1]) * 100,
            )
        )

    nr_of_correlation_pixels = np.count_nonzero(Landsat_B8_mask == 0)
    logging.info(
        "Running correlation for %s pixels (%02.1f %%)"
        % (
            f"{nr_of_correlation_pixels:,}",
            nr_of_correlation_pixels
            / (Landsat_B8_mask.shape[0] * Landsat_B8_mask.shape[1])
            * 100,
        )
    )

    geotiff_fn = os.path.join(
        tifdirname,
        os.path.basename(dirname)
        + "_bs%02d_sr%02d_ms%02d_mask.tif"
        % (
            block_size,
            search_radius,
            matching_step,
        ),
    )
    logging.info("Save geotiff to %s" % (geotiff_fn))
    save_mask_geotiff(
        geotiff_fn, Landsat_B8_mask, epsg_code, geotransform=Landsat_1_ds_gt
    )

    logging.info(
        "Running block matching for %s and %s with block size: %02d and search radius %02d and matching step %02d and nthreads_exp %02d"
        % (fname1, fname2, block_size, search_radius, matching_step, nthreads_exp)
    )
    start = time.time()
    # block_matching_masked_ncc_uint_nonzero(p, q, mask, block_size, search_radius, nthreads_exp=10)
    u, v, correlation = block_matching_masked_ncc_uint_nonzero(
        Landsat_B8_1,
        Landsat_B8_2,
        Landsat_B8_mask,
        block_size,
        search_radius,
        nthreads_exp=nthreads_exp,
    )
    end = time.time()
    length_s = end - start
    logging.info("Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60))

    start = time.time()
    save_all_geotiff(tifdirname)
    end = time.time()
    length_s = end - start
    logging.info(
        "Writing all tiles took %d seconds or %2.2f minutes" % (length_s, length_s / 60)
    )
    end = time.time()

    length_s = end - start0
    logging.info(
        "All steps combined took %d seconds or %2.2f minutes or %2.2f hours "
        % (length_s, length_s / 60, length_s / (60 * 60))
    )
