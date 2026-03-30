import numpy as np
import os, logging, time, sys, glob, tqdm, warnings

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


def create_fnames_from_csv(csv_fname, dirname):
    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    logging.info("Loading %d files" % len(date_pairs))
    logging.info("Data directory is %s" % (dirname))
    oversampling = int(os.path.basename(dirname).split("_")[1][2:])
    block_size = int(os.path.basename(dirname).split("_")[2][2:])
    search_radius = int(os.path.basename(dirname).split("_")[3][2:])
    matching_step = int(os.path.basename(dirname).split("_")[4][2:])
    outfile_png = []
    for i in range(len(date_pairs)):
        outfname_png = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_u.png" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_png = os.path.join(dirname, outfname_png)
        if not os.path.exists(outfname_png):
            logging.info("%s does not exists" % outfname_png)
        outfile_png.append(outfname_png)
    return outfile_png


if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")

    csv_fname = sys.argv[1]
    png_dirname = sys.argv[2]

    # csv_fname = "corr_dates_sd1_cc30_B"
    # png_dirname = "CORR_os05_bs91_sr06_ms05_u_png"

    # Loading PNG files
    outfile_png = create_fnames_from_csv(csv_fname, png_dirname)

    with open("%s.filelist" % csv_fname, "w") as f:
        for line in outfile_png:
            f.write(f"{line}\n")

    # run magick:
    # magick @corr_dates_sd1_cc30_B.filelist -compress jpeg corr_dates_sd1_cc30_B.pdf
