#!/usr/bin/env bash

# Submit all tiles for block matching in a specific directory to the slurm queue
# Input:  Basedir where log files are stored
#         Directory1 (reference tiles)
#         Directory2 (secondary tiles)
#         block size
#         search radius
#
#block_matching_slurm.bash /raid2-gpu2/bodo/Landsat-test/231077/ \
#  /raid2-gpu2/bodo/Landsat-test/231077/20130820_os01 \
#  /raid2-gpu2/bodo/Landsat-test/231077/20240420_os01 \
#  21 5

toolpath=/raid2-gpu2/bodo/Landsat-test
basedir=$1
refdir=$2
secdir=$3
tilesize=$4
blocksize=$5
searchradius=$6

#where we store all bash and python files - needs to be on NFS
#basedir=/raid2-gpu2/bodo/Landsat-test/231077
#cd /raid2-gpu2/bodo/Landsat-test
#refdir=/raid2-gpu2/bodo/Landsat-test/231077/20130820_os01
#secdir=/raid2-gpu2/bodo/Landsat-test/231077/20240420_os01
#blocksize=21
#searchradius=5
#tilesize=4096

cd $basedir
if [ ! -d "log" ]; then
	mkdir log
fi

if [ ! -d "slurm.bash" ]; then
	mkdir slurm.bash
fi

submit_slurm_block_matching_ids=()
for reffile in ${refdir}/*_${tilesize}_os??_*.npy; do
	reffile_basename=$(basename $reffile)
	#this is a cheap way of getting the tile number - will need to be adjusted of filelength changes
	tilenr=${reffile_basename:54:2}
	os=${reffile_basename:49:4}
	refyear=${reffile_basename:17:8}
	secfile=$(ls -1 $secdir/*os*_${tilenr}.npy)
	secfile_basename=$(basename $secfile)
	secyear=${secfile_basename:17:8}
	file2process=${basedir}/slurm.bash/${refyear}_${secyear}_${os}_${tilenr}_bs${blocksize}_sr${searchradius}.bash
	logfile=$basedir/log/${refyear}_${secyear}_${tilesize}_${os}_${tilenr}_bs${blocksize}_sr${searchradius}.bash.log
	errfile=$basedir/log/${refyear}_${secyear}_${tilesize}_${os}_${tilenr}_bs${blocksize}_sr${searchradius}.bash.err

	# create bash file with commands to be passed on to slurm
	echo "python $toolpath/run_block_matching.py $reffile $secfile $blocksize $searchradius" >$file2process
	sed -i '1i #!/usr/bin/env bash ' $file2process
	sed -i '2i echo "HOSTNAME: `hostname`"' $file2process
	sed -i '3i source /raid-everest/conda/miniconda3/etc/profile.d/conda.sh' $file2process
	sed -i '4i conda activate tensorflow' $file2process
	sed -i '5i conda info' $file2process
	sed -i "6i export PATH=$PATH:$toolpath" $file2process
	sed -i "7i cd $basedir" $file2process
	submit_slurm_block_matching_ids=$(
		sbatch --parsable -G=1 --mem-per-gpu=2G --partition=gpu_all --cpus-per-gpu=2 --time=24:00:00 --output=$logfile --error=$errfile $file2process
	)
	echo submitted ${refyear}_${secyear}_${tilenr}_${os}_bs${blocksize}_sr${searchradius}
	#echo ${submit_slurm_block_matching_ids}
done

# hack to get process ids from slurm queue
# this may be used to trigger merging of tiles - only if all tiles have been processed
# -dependency=afterok the merging will be triggered. Not implemented yet.
#read -ra foo <<<${submit_slurm_block_matching_ids}
#submit_slurm_block_matching_pid=${foo[3]}
#echo ${submit_slurm_block_matching_pid[@]} >block_matching_slurm_ids.txt
echo ${submit_slurm_block_matching_ids}
#sed -i 's# #:#g' submit_slurm_block_matching_ids.txt
#sed -i '1s/^/--dependency=afterok:/' submit_slurm_block_matching_ids.txt
