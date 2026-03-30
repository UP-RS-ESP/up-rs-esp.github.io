import numpy as np
import os, logging, glob, sys


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
# maybe add #SBATCH --nodelist=hgc02 for large GPU memory node
JOBHEADER = """#!/bin/bash

#SBATCH --partition=gpu              # on the partition "gpu"
#SBATCH --nodes=1                    # on a single node
#SBATCH --ntasks=1                   # with a single task (this should always be 1, apart from special cases)
#SBATCH --cpus-per-task=2            # with that many cpu cores
#SBATCH --mem=300GB                  # will require that amount of RAM at maximum (if the process takes more it gets killed)
#SBATCH --gres=gpu:2                 # get both GPUs on node
#SBATCH --time=0-06:00               # maximum runtime of the job as "d-hh:mm"
#SBATCH --chdir=/work/bookhage/Landsat/P231R076   # working directory of the job
#SBATCH --mail-type=FAIL             # always get mail notifications
#SBATCH --output=slurm-%j.out        # standard out of the job into this file (also stderr)

echo HOSTNAME: `hostname`
source /home/bookhage/miniconda3/etc/profile.d/conda.sh
conda activate numba
conda info

"""

if __name__ == "__main__":
    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching_mask.py \
    # /work/bookhage/Landsat/P231R076/corr_dates_sd1_cc30_B \
    # /work/bookhage/Landsat/P231R076/run_block_matching_231076_os01_bs121_sr15_ms01.bash \
    # 231076 121 15 5 1 1 \
    # /work/bookhage/Landsat/P231R076/CORR_os05_bs121_sr15_ms01 \
    # /work/bookhage/Landsat/P231R076/251210_landslide_buffer_P231R076_os5.tif
    # python /work/bookhage/Landsat/code/slurm_blockmatching/create_runfile_fullscene_blockmatching_mask.py \
    # /work/bookhage/Landsat/P231R076/corr_dates_sd1_cc30_B \
    # /work/bookhage/Landsat/P231R076/run_block_matching_231076_os01_bs121_sr15_ms01.bash \
    # 231076 91 15 5 1 1 \
    # /work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr15_ms01 \
    # /work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc30_B_median_velocity_magnitude_my_gf_cc1e4m2_filt_os05.tif

    csv_fname = sys.argv[1]
    runfile_out = sys.argv[2]
    pathrow = sys.argv[3]
    block_size = int(sys.argv[4])
    search_radius = int(sys.argv[5])
    oversampling = int(sys.argv[6])
    matching_step = int(sys.argv[7])
    nr_jobs_per_cuda = int(sys.argv[8])
    tifdirname = sys.argv[9]
    maskfname = sys.argv[10]
    cudadevice = 0

    # csv_fname = "/work/bookhage/Landsat/P231R076/corr_dates_sd1_cc30_B"
    # runfile_out = "/work/bookhage/Landsat/P231R076/run_block_matching_231076_os01_bs121_sr09_ms01.bash"
    # pathrow = "231076"
    # block_size = 121
    # search_radius = 9
    # oversampling = 5
    # matching_step = 1
    # nr_jobs_per_cuda = 1
    # tifdirname ='/work/bookhage/Landsat/P231R076/CORR_os05_bs121_sr09_ms01'
    # maskfname='/work/bookhage/Landsat/P231R076/251210_landslide_buffer_P231R076.tif'
    # maskfname='/work/bookhage/Landsat/P231R076/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc30_B_median_velocity_magnitude_my_cc1e4m2_bbox_filtered_buffered45m_mask_os05.tif'

    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    data_dir = os.path.dirname(csv_fname)
    if oversampling > 1:
        data_dir = os.path.join(data_dir, "CROP_os%02d" % oversampling)
    else:
        data_dir = os.path.join(data_dir, "CROP")
    logging.info("Data directory is %s" % (data_dir))
    commands = []
    sbatch_commands = []
    counter = 0
    jobcounter = 0
    # Create jobs that submit the block matching to each cudadevice. There are two cuda devices on the HPC nodes
    for i in range(len(date_pairs)):
        outpath = "CORR_os%02d_bs%02d_sr%02d_ms%02d" % (
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfname_correlation = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_correlation.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfile_correlation = os.path.join(outpath, outfname_correlation)
        outfname_mask = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_mask.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfile_mask = os.path.join(outpath, outfname_mask)
        outfname_u = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_u.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfile_u = os.path.join(outpath, outfname_u)
        outfname_v = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_v.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfile_v = os.path.join(outpath, outfname_v)
        outfname_stddev = "%d_%d_os%02d_bs%02d_sr%02d_ms%02d_stddev.tif" % (
            date_pairs[i, 0],
            date_pairs[i, 1],
            oversampling,
            block_size,
            search_radius,
            matching_step,
        )
        outfile_stddev = os.path.join(outpath, outfname_stddev)
        if (
            os.path.exists(outfile_correlation)
            and os.path.exists(outfile_mask)
            and os.path.exists(outfile_u)
            and os.path.exists(outfile_v)
            and os.path.exists(outfile_stddev)
        ):
            logging.info(
                "Output files %s exists, continuing to next file." % outfile_mask
            )
            continue

        fname1 = glob.glob(
            os.path.join(data_dir, "L*_L1TP_%s_%d_*.TIF" % (pathrow, date_pairs[i, 0]))
        )
        if fname1 == []:
            logging.info("fname1 could not be found for date %d" % date_pairs[i, 0])
            continue
        fname2 = glob.glob(
            os.path.join(data_dir, "L*_L1TP_%s_%d_*.TIF" % (pathrow, date_pairs[i, 1]))
        )
        if fname2 == []:
            logging.info("fname2 could not be found for date %d" % date_pairs[i, 1])
            continue

        commands.append(
            "python /work/bookhage/Landsat/code/slurm_blockmatching/run_fullscene_block_matching_mask.py %s %s %d %d %d %d %d %s %s 2>&1 | tee log/run_fullscene_block_matching_%s_os%02d_bs%02d_sr%02d_ms%02d_%d_%d_cudadevice%d.log &"
            % (
                fname1[0],
                fname2[0],
                block_size,
                search_radius,
                oversampling,
                matching_step,
                cudadevice,
                tifdirname,
                maskfname,
                pathrow,
                oversampling,
                block_size,
                search_radius,
                matching_step,
                date_pairs[i, 0],
                date_pairs[i, 1],
                int(cudadevice),
            )
        )
        commands.append("sleep 30s")

        if cudadevice == 0:
            cudadevice = 1
        else:
            cudadevice = 0
            counter += 1

        if counter == nr_jobs_per_cuda:
            # write to file
            runfile_out_jobfn = runfile_out[:-5] + "_job%03d.bash" % jobcounter
            logging.info("Writing to file %s" % runfile_out_jobfn)
            with open(runfile_out_jobfn, "w") as f:
                f.write(JOBHEADER + "\n")
                for line in commands:
                    f.write(f"{line}\n")
                f.write("\n")
                f.write("wait\n")
            commands = []
            counter = 0
            jobcounter += 1
            sbatch_commands.append("sbatch %s" % runfile_out_jobfn)
            # sbatch_commands.append("sleep 30s")

        if i == len(date_pairs) - 1:
            # last iteration in for loop - write file
            runfile_out_jobfn = runfile_out[:-5] + "_job%03d.bash" % jobcounter
            logging.info("Writing to file %s" % runfile_out_jobfn)
            with open(runfile_out_jobfn, "w") as f:
                f.write(JOBHEADER + "\n")
                for line in commands:
                    f.write(f"{line}\n")
                f.write("\n")
                f.write("wait\n")
            commands = []
            sbatch_commands.append("sbatch %s" % runfile_out_jobfn)

    sbatch_fname = "run_sbatch_%s_os%02d_bs%02d_sr%02d_ms%02d.bash" % (
        pathrow,
        oversampling,
        block_size,
        search_radius,
        matching_step,
    )
    logging.info("Writing to sbatch command file %s" % sbatch_fname)
    logging.info("Run with: \n. ./%s" % sbatch_fname)
    with open(sbatch_fname, "w") as f:
        for line in sbatch_commands:
            f.write(f"{line}\n")
