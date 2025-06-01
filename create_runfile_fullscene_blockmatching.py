import numpy as np
import os, logging, glob, sys


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

JOBHEADER = """#!/bin/bash

#SBATCH --partition=gpu              # on the partition "gpu"
#SBATCH --nodes=1                    # on a single node
#SBATCH --ntasks=1                   # with a single task (this should always be 1, apart from special cases)
#SBATCH --cpus-per-task=2            # with that many cpu cores
#SBATCH --mem=256GB                  # will require that amount of RAM at maximum (if the process takes more it gets killed)
#SBATCH --gres=gpu:2                 # get both GPUs on node
#SBATCH --time=0-08:00               # maximum runtime of the job as "d-hh:mm"
#SBATCH --chdir=/work/bookhage/Landsat/P232R077   # working directory of the job
#SBATCH --mail-type=ALL              # always get mail notifications
#SBATCH --output=slurm-%j.out        # standard out of the job into this file (also stderr)

echo HOSTNAME: `hostname`
source /home/bookhage/miniconda3/etc/profile.d/conda.sh
conda activate numba
conda info

"""

if __name__ == "__main__":

    # python create_runfile_fullscene_blockmatching.py \
    # /work/bookhage/Landsat/P001R077/corr_dates_sd1_cc23 \
    # /work/bookhage/Landsat/P001R077/run_block_matching_001077_os01_bs31_sr03_ms01.bash \
    # 001077 31 3 1 1 10
    csv_fname = sys.argv[1]
    runfile_out = sys.argv[2]
    pathrow = sys.argv[3]
    block_size = int(sys.argv[4])
    search_radius = int(sys.argv[5])
    oversampling = int(sys.argv[6])
    matching_step = int(sys.argv[7])
    nr_jobs_per_cuda = int(sys.argv[8])
    cudadevice = 0

    # csv_fname = "/work/bookhage/Landsat/P001R077/corr_dates_sd1_cc23"
    # runfile_out = "/work/bookhage/Landsat/P001R077/run_block_matching_001077_os01_bs31_sr03_ms01.bash"
    # pathrow = "001077"
    # block_size = 31
    # search_radius = 3
    # oversampling = 1
    # matching_step = 1
    # nr_jobs_per_cuda = 10

    date_pairs = np.genfromtxt(csv_fname, delimiter=",")
    data_dir = os.path.dirname(csv_fname)
    data_dir = os.path.join(data_dir, "CROP_os03")
    logging.info("Data directory is %s" % (data_dir))
    commands = []
    sbatch_commands = []
    counter = 0
    jobcounter = 0
    # Create jobs that submit the block matching to each cudedevice. There are two cuda devices on the HPC nodes
    for i in range(len(date_pairs)):
        fname1 = glob.glob(
            os.path.join(data_dir, "LC*_L1TP_%s_%d*.TIF" % (pathrow, date_pairs[i, 0]))
        )
        fname2 = glob.glob(
            os.path.join(data_dir, "LC*_L1TP_%s_%d*.TIF" % (pathrow, date_pairs[i, 1]))
        )
        commands.append(
            "python /work/bookhage/Landsat/code/slurm_blockmatching/run_fullscene_block_matching.py %s %s %d %d %d %d %d 2>&1 | tee log/run_fullscene_block_matching_%s_os%02d_bs%02d_sr%02d_ms%02d_%d_%d_cudadevice%d.log &"
            % (
                fname1[0],
                fname2[0],
                block_size,
                search_radius,
                oversampling,
                matching_step,
                cudadevice,
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

    logging.info("Writing to sbatch command file sbatch.run.bash")
    logging.info("Run with: . ./sbatch.run.bash")
    with open("sbatch.run.bash", "w") as f:
        for line in sbatch_commands:
            f.write(f"{line}\n")
