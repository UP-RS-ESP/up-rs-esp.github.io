python code/slurm_blockmatching/create_Landsat_tiles.py /work/bookhage/Landsat/os05 4096 64 3 2>&1 | tee log/create_Landsat_tiles_P232R077_4096_64_3.log



# For tile0:
uimg_ts64_2013_0 = np.load(
    "231077/20130820_20240420_os01/20130820_20240420_8192_os01_00_bs21_sr06_u.npy"
)
uimg_ts32_2013_0 = np.load(
    "231077/20130820_20240420_os01_tilesize32/20130820_20240420_8192_os01_00_bs21_sr06_u.npy"
)
ax1 = plt.subplot(1, 2, 1)
ax1.set_title("tilesize 32")
ax1.imshow(uimg_ts32_2013_0[32 : 8192 + 32, 32 - 16 : 8192 + 32 - 16])
ax2 = plt.subplot(1, 2, 2, sharex=ax1, sharey=ax1)
ax2.set_title("tilesize 64")
ax2.imshow(uimg_ts64_2013_0[64 : 8192 + 64, 64 - 16 : 8192 + 64 - 16])
plt.show()

# For tile1:
uimg_ts64_2013_1 = np.load(
    "231077/20130820_20240420_os01/20130820_20240420_8192_os01_01_bs21_sr06_u.npy"
)
uimg_ts32_2013_1 = np.load(
    "231077/20130820_20240420_os01_tilesize32/20130820_20240420_8192_os01_01_bs21_sr06_u.npy"
)
ax1 = plt.subplot(1, 2, 1)
ax1.set_title("tilesize 32")
ax1.imshow(uimg_ts32_2013_1[32 : 8192 + 32, 32 - 16 : 8192 + 32 - 16])
ax2 = plt.subplot(1, 2, 2, sharex=ax1, sharey=ax1)
ax2.set_title("tilesize 64")
ax2.imshow(uimg_ts64_2013_1[64 : 8192 + 64, 64 - 32 - 16 : 8192 + 64 - 32 - 16])
plt.show()

# For tile2:
uimg_ts64_2013_2 = np.load(
    "231077/20130820_20240420_os01/20130820_20240420_8192_os01_02_bs21_sr06_u.npy"
)
uimg_ts32_2013_2 = np.load(
    "231077/20130820_20240420_os01_tilesize32/20130820_20240420_8192_os01_02_bs21_sr06_u.npy"
)
ax1 = plt.subplot(1, 2, 1)
ax1.set_title("tilesize 32")
ax1.imshow(uimg_ts32_2013_2[32 - 16 : 8192 + 32 - 16, 32 - 16 : 8192 + 32 - 16])
ax2 = plt.subplot(1, 2, 2, sharex=ax1, sharey=ax1)
ax2.set_title("tilesize 64")
ax2.imshow(
    uimg_ts64_2013_2[64 - 32 - 16 : 8192 + 64 - 32 - 16, 64 - 16 : 8192 + 64 - 16]
)
plt.show()

# For tile3:
uimg_ts64_2013_3 = np.load(
    "231077/20130820_20240420_os01/20130820_20240420_8192_os01_03_bs21_sr06_u.npy"
)
uimg_ts32_2013_3 = np.load(
    "231077/20130820_20240420_os01_tilesize32/20130820_20240420_8192_os01_03_bs21_sr06_u.npy"
)
ax1 = plt.subplot(1, 2, 1)
ax1.set_title("tilesize 32")
ax1.imshow(uimg_ts32_2013_3[32 - 16 : 8192 + 32 - 16, 32 - 16 : 8192 + 32 - 16])
ax2 = plt.subplot(1, 2, 2, sharex=ax1, sharey=ax1)
ax2.set_title("tilesize 64")
ax2.imshow(
    uimg_ts64_2013_3[
        64 - 32 - 16 : 8192 + 64 - 32 - 16, 64 - 32 - 16 : 8192 + 64 - 32 - 16
    ]
)
plt.show()

# For dim0: overlap (dim0==0), overlap-overlap/2-overlap/4 or just overlap/4 (dim>0)
# For dim1: overlap-(overlap/4)

# Tile2 Landsat data
L8img_ts64_2013_2 = np.load(
    "231077/20130820_os01/LC08_L1TP_231077_20130820_20200913_02_T1_B8_8192_os01_02.npy"
)
ax1 = plt.subplot(1, 2, 1)
ax1.set_title("tilesize 64-L8")
ax1.imshow(L8img_ts64_2013_2)  # [32-16:8192+32-16,32-16:8192+32-16])
ax2 = plt.subplot(1, 2, 2, sharex=ax1, sharey=ax1)
ax2.set_title("tilesize 64")
ax2.imshow(uimg_ts64_2013_2)  # [64-32-16:8192+64-32-16, 64-16:8192+64-16])
plt.show()
