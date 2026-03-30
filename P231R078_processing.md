# Postprocessing

## A - no oversampling

```bash
mkdir log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_u_png
magick @corr_dates_sd1_cc20_A.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_A.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A 2>&1 | tee log/run_ramp_fitting_fromcsv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_A.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_A.log
magick @CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_Aramp.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_rampoverview_corr_dates_sd1_cc20_A.pdf



python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_tilesoverview_png
magick @corr_dates_sd1_cc20_A_u.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_A_u.pdf
magick @corr_dates_sd1_cc20_A_v.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_A_v.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_B_nre_velocity.tif
```

# A - os05

```bash
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_u_png
magick @corr_dates_sd1_cc20_A.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_A.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A 2>&1 | tee log/run_ramp_fitting_from_csv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_A.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_A.log
magick @CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_Aramp.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_rampoverview_corr_dates_sd1_cc20_A.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_tilesoverview_png
magick @corr_dates_sd1_cc20_A_u.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_A_u.pdf
magick @corr_dates_sd1_cc20_A_v.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_A_v.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_A

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_A_median_velocity_magnitude_my.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_A_nre_velocity.tif
```

## B - no oversampling

```bash
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_u_png
magick @corr_dates_sd1_cc20_B.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_B.pdf


python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B 2>&1 | tee log/run_ramp_fitting_from_csv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_B.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_B.log
magick @CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_Bramp.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_rampoverview_corr_dates_sd1_cc20_B.pdf


python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_LindarND_fitting_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_tilesoverview_png
magick @corr_dates_sd1_cc20_B_u.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_B_u.pdf
magick @corr_dates_sd1_cc20_B_v.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_B_v.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my.tif \
  CORR_os05_bs61_sr06_ms05_corr_dates_sd1_cc20_B_nre_velocity.tif
```

## B - os05

```bash
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_u_png
magick @corr_dates_sd1_cc20_B.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B 2>&1 | tee log/run_ramp_fitting_from_csv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B.log
magick @CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_Bramp.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_rampoverview_corr_dates_sd1_cc20_B.pdf


python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_LindarND_fitting_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_tilesoverview_png
magick @corr_dates_sd1_cc20_B_u.filelist -compress jpeg P231R078_BORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_B_u.pdf
magick @corr_dates_sd1_cc20_B_v.filelist -compress jpeg P231R078_BORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_B_v.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_B

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my.tif \
  CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B_nre_velocity.tif
```

## C - no oversampling

```bash
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_u_png
magick @corr_dates_sd1_cc20_C.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_C.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C 2>&1 | tee log/run_ramp_fitting_from_csv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_C.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_C.log
magick @CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_Cramp.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_rampoverview_corr_dates_sd1_cc20_C.pdf

# python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_LindarND_fitting_from_csv.py \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
#   /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C
# python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_tilesoverview_png
# magick @corr_dates_sd1_cc20_C_u.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_C_u.pdf
# magick @corr_dates_sd1_cc20_C_v.filelist -compress jpeg P231R078_CORR_os01_bs41_sr03_ms01_tileoverview_corr_dates_sd1_cc20_C_v.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs41_sr03_ms01_\
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_C_median_velocity_magnitude_my.tif \
  CORR_os01_bs41_sr03_ms01_corr_dates_sd1_cc20_C_nre_velocity.tif
```

## C - os05

```bash
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_convert_block_matching_fromcsv.py  \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05 \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os01_bs11_sr03_ms01/ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_from_csv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_u_png
magick @corr_dates_sd1_cc20_C.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_C.pdf

python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C 2>&1 | tee log/run_ramp_fitting_from_csv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_C.log
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/plot_ramp_fitting_fromcsv.py \
  /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
  /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C 2>&1 | tee log/plot_ramp_fitting_fromcsv_CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_C.log
magick @CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_Cramp.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_rampoverview_corr_dates_sd1_cc20_C.pdf

# python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_ramp_LindarND_fitting_from_csv.py \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_\
#   /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C
# python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/combine_pngs_tileoverview_from_csv.py \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C \
#   /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_tilesoverview_png
# magick @corr_dates_sd1_cc20_C_u.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_C_u.pdf
# magick @corr_dates_sd1_cc20_C_v.filelist -compress jpeg P231R078_CORR_os05_bs91_sr06_ms05_tileoverview_corr_dates_sd1_cc20_C_v.pdf
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_averaged_velocities_fromcsv.py  \
    /raid2-gpu2/bodo/LANDSAT/P231R078/CORR_os05_bs91_sr06_ms05_ \
    /raid2-gpu2/bodo/LANDSAT/P231R078/COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
    /raid2-gpu2/bodo/LANDSAT/P231R078/corr_dates_sd1_cc20_C
python /raid2-gpu2/bodo/LANDSAT/code/slurm_blockmatching/run_connected_component.py \
  COP15_DEM_ARGENTINA_UTM20_P231R078.tif \
  CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_C_median_velocity_magnitude_my.tif \
  CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_C_nre_velocity.tif
```

```bash
rsync -avz P231R078*png *pdf bodo@macon.geo.uni-potsdam.de:/home/bodo/Dropbox/foo/P231R078
rsync -avz *gpkg P231R078*png *pdf CORR*.tif bodo@macon.geo.uni-potsdam.de:/home/bodo/Dropbox/foo/P231R078

```

gdal_rasterize -l CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my_filt_cc1e4m2_bbox \
  -burn 1.0 -tr 15.0 15.0 -a_nodata 0.0 -te 179692.5 -2660407.5 400207.5 -2453692.5 \
  -ot Byte -of GTiff -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
  /home/bodo/Dropbox/foo/P231R078/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my_filt_cc1e4m2_bbox.gpkg \
  /home/bodo/Dropbox/foo/P231R078/CORR_os05_bs91_sr06_ms05_corr_dates_sd1_cc20_B_median_velocity_magnitude_my_gf_cc1e4m2_filt.tif

gdal_rasterize -l 251210_landslides_NWArg_buffer2500 -burn 1.0 -tr 15.0 15.0 \
  -a_nodata 0.0 -te 114892.5 -2986507.5 333907.5 -2769592.5 \
  -ot Byte -of GTiff -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 \
  /home/bodo/Dropbox/foo/P231R078/251210_landslides_NWArg_buffer2500.gpkg \
  /home/bodo/Dropbox/foo/P231R078/251210_landslide_buffer_P231R078.tif
