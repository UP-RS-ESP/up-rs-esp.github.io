import numpy as np
import os, logging, time, sys, glob, tqdm, warnings
import pandas as pd
import matplotlib

# matplotlib.use("Agg")
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

    u_stats_df = pd.read_csv("corr_dates_sd1_cc29_u_stats.csv", index_col="filenr")
    u_stats_df["date1"] = pd.to_datetime(u_stats_df.date1, format="%Y-%m-%d")
    u_stats_df["date2"] = pd.to_datetime(u_stats_df.date2, format="%Y-%m-%d")
    float64_cols = list(u_stats_df.select_dtypes(include="float64"))
    u_stats_df[float64_cols] = u_stats_df[float64_cols].astype("float32")

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(12, 8), dpi=300, layout="constrained", sharex=True
    )
    ax1.plot(u_stats_df.date1, u_stats_df.umean, "o", label="Mean u")
    ax1.grid()
    ax1.set_ylabel("u mean [m/y]")
    ax2.plot(u_stats_df.date1, u_stats_df.uvar, "x", label="Var u")
    ax2.grid()
    ax2.set_ylabel("u var [m/y]")
    ax3.plot(u_stats_df.date1, u_stats_df.p1_slope_deg, "s", label="P1 Slope")
    ax3.grid()
    ax3.set_ylabel("p1 slope_deg")
    ax3.set_xlabel("First Date")
    fig.savefig("U_timeseries_statistics.png")

    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3, figsize=(12, 8), dpi=300, layout="constrained"
    )
    ax1.plot(u_stats_df.umean, u_stats_df.uvar, "x", label="Mean u")
    ax1.grid()
    ax1.set_xlabel("u mean [m/y]")
    ax1.set_ylabel("u var [m/y]")
    ax2.plot(u_stats_df.umean, u_stats_df.p1_slope_deg, "x")
    ax2.set_xlabel("u mean [m/y]")
    ax2.set_ylabel("p1 slope [deg]")
    ax2.grid()
    ax3.plot(u_stats_df.p1_slope_deg, u_stats_df.p2_slope_deg, "s")
    ax3.grid()
    ax3.set_xlabel("p1 slope [deg]")
    ax3.set_ylabel("p2 slope [deg]")
    fig.savefig("U_scatterplots_statistics.png")
