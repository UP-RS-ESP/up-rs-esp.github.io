import pandas as pd
import numpy as np
import os, logging, time, sys, glob, tqdm, warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

if __name__ == "__main__":
    np.seterr(divide="ignore", invalid="ignore")
    warnings.filterwarnings("ignore")
    matplotlib.pyplot.set_loglevel(level="warning")

    ucsv_fname = sys.argv[1]
    vcsv_fname = sys.argv[2]

    ucsv_fname = "corr_dates_sd1_cc20_B_u_stats.csv"
    vcsv_fname = "corr_dates_sd1_cc20_B_v_stats.csv"

    u_stats = pd.read_csv(ucsv_fname, index_col="filenr")
    u_stats["date1"] = pd.to_datetime(u_stats.date1)
    u_stats["date2"] = pd.to_datetime(u_stats.date2)
    u_stats = u_stats.infer_objects()
    v_stats = pd.read_csv(vcsv_fname, index_col="filenr")
    v_stats["date1"] = pd.to_datetime(v_stats.date1)
    v_stats["date2"] = pd.to_datetime(v_stats.date2)
    v_stats = v_stats.infer_objects()

    pngfn = ucsv_fname[:-11] + "uv_stats.png"
    fig_title = pngfn
    fig, ax = plt.subplots(
        nrows=3, ncols=2, sharex=True, figsize=(16, 9), dpi=300, layout="constrained"
    )
    ax[0, 0].plot(
        u_stats.date1,
        u_stats.p1_slope_deg / 1e3,
        color="navy",
        label="u-plane slope (degree)",
    )
    ax[0, 0].plot(
        v_stats.date1,
        v_stats.p1_slope_deg / 1e3,
        color="firebrick",
        label="v-plane slope (degree)",
    )
    ax[0, 0].grid()
    # ax[0,0].set_xlabel('Date')
    ax[0, 0].set_ylabel("Detrending Plane (degree x $10^{-3}$)")
    ax[0, 1].plot(u_stats.date1, u_stats.p1_rmse, color="navy", label="u-plane RMSE")
    ax[0, 1].plot(
        v_stats.date1, v_stats.p1_rmse, color="firebrick", label="v-plane RMSE"
    )
    ax[0, 1].grid()
    ax[0, 1].set_xlabel("Date")
    ax[0, 1].set_ylabel("Detrending Plane (RMSE)")
    fig.suptitle("%s" % (fig_title))
    fig.savefig(pngfn, dpi=300)
    plt.close()
