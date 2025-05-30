import numpy as np
import numba as nb
from block_matching import block_matching_ncc, block_matching_masked_ncc
from numba import cuda
from math import sqrt

import os, logging, time, sys

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


if __name__ == "__main__":

    fname1 = sys.argv[1]
    fname2 = sys.argv[2]
    tile_size = int(sys.argv[3])
    block_size = int(sys.argv[4])
    search_radius = int(sys.argv[5])
    matching_step = int(sys.argv[6])

    # fname1 = "231077/20130820_os01/LC08_L1TP_231077_20130820_20200913_02_T1_B8_8192_os01_03.npy"
    # fname2 = "231077/20240420_os01/LC09_L1TP_231077_20240420_20240420_02_T1_B8_8192_os01_03.npy"
    # block_size = 21
    # search_radius = 6
    # tile_size = 8192
    # matching_step = 1

    logging.info(
        "Running block matching for %s and %s with tile size: %d, block size: %02d, and search radius %02d"
        % (fname1, fname2, tile_size, block_size, search_radius)
    )
    p = np.load(fname1)
    q = np.load(fname2)
    year_name1 = os.path.basename(fname1).split("_")[3]
    year_name2 = os.path.basename(fname2).split("_")[3]
    patch_nr = os.path.basename(fname1).split("_")[-1].split(".")[0]
    oversampling = os.path.basename(fname1).split("_")[-2].split(".")[0]
    fname = "%s_%s_%04d_%s_%s_bs%02d_sr%02d" % (
        year_name1,
        year_name2,
        tile_size,
        oversampling,
        patch_nr,
        block_size,
        search_radius,
    )
    dirname = "%s_%s_%s" % (year_name1, year_name2, oversampling)
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    start = time.time()
    if matching_step == 1:
        u, v, block_sizes, correlation = block_matching_ncc(
            p, q, block_size, search_radius
        )
    else:
        # mask == 1 is masked out and will not be processed
        mask = np.ones(p.shape, dtype=np.bool_)
        mask[::matching_step, ::matching_step] = 0
        u, v, block_sizes, correlation = block_matching_masked_ncc(
            p, q, mask, block_size, search_radius
        )
    end = time.time()
    length_s = end - start
    logging.info("Tile took %d seconds or %2.2f minutes" % (length_s, length_s / 60))
    write_patch_correlation_npy(
        u,
        v,
        block_sizes,
        correlation,
        dirname,
        fname,
    )
    logging.info("Wrote u, v, block sizes and correlation files for %s" % fname)
