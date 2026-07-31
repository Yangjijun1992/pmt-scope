"""plot_gain.py — SPE Gain 独立绘图脚本

图1: 直方图，bins=30，x_range=[0, 20]，去除 hv > 800V 数据
图2: vs PMT ID 散点图，3σ 离群点标注
     - xr* run_id: 三角形 (^)
     - 纯数字 run_id: 圆形 (o)

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/gain_histogram.png, figs/gain_scatter.png
"""

import os
import re
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pmt-data-client", "data", "pmt_data.db")
FIGS_DIR = os.path.join(os.path.dirname(__file__), "..", "figs")
GAIN_X_MIN, GAIN_X_MAX = 0.0, 20.0
GAIN_BINS = 30
SIGMA_MULTIPLIER = 3.0

COLOR_BAR = "#4C78A8"
COLOR_MEDIAN = "#333333"
COLOR_XR = "#D62728"
COLOR_NUM = "#2B6FB3"
COLOR_OUTLIER = "#D62728"
COLOR_OVERLAP = "#9467BD"   # 紫色: 科大+西湖重复计数 PMT


def _load_overlap_pmts() -> set:
    path = os.path.join(os.path.dirname(__file__), "..", "docs", "overlap_pmt_ids.csv")
    if os.path.exists(path):
        try:
            overlap_df = pd.read_csv(path)
            return set(overlap_df["pmt_id"].dropna().tolist())
        except Exception:
            return set()
    return set()


def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               channel_id,
               run_id,
               hv,
               AVG(spe_gain) AS spe_gain
        FROM measurements
        WHERE spe_gain IS NOT NULL
        GROUP BY pmt_id, channel_id, run_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Remove records with hv > 800V
    df = df[df["hv"] <= 800].copy()

    df["run_type"] = df["run_id"].apply(
        lambda x: "xr" if bool(re.match(r"^xr", str(x))) else "numeric"
    )

    df.sort_values(["pmt_id", "channel_id", "run_type"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def plot_histogram(df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(df["spe_gain"], bins=GAIN_BINS, color=COLOR_BAR, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    ax.set_xlabel("Gain [e$^{-}$]", fontsize=16, x=0.94, ha="right")
    ax.set_ylabel("Counts", fontsize=16)
    ax.set_title("SPE Gain Distribution (hv ≤ 800 V)", fontsize=18, fontweight="bold")
    ax.set_xlim(GAIN_X_MIN, GAIN_X_MAX)
    ax.tick_params(axis="both", labelsize=14)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def plot_scatter(df: pd.DataFrame, out_path: str, overlap_pmts: set):
    median_val = df["spe_gain"].median()
    mean_val = df["spe_gain"].mean()
    std_val = df["spe_gain"].std()
    lower_bound = mean_val - SIGMA_MULTIPLIER * std_val
    upper_bound = mean_val + SIGMA_MULTIPLIER * std_val

    is_outlier = (df["spe_gain"] < lower_bound) | (df["spe_gain"] > upper_bound)
    is_normal = ~is_outlier

    is_overlap = df["pmt_id"].isin(overlap_pmts)

    fig, ax = plt.subplots(figsize=(18, 6))

    xr_normal = df[(df["run_type"] == "xr") & is_normal]
    xr_outlier = df[(df["run_type"] == "xr") & is_outlier]
    num_normal_nohl = df[(df["run_type"] == "numeric") & is_normal & ~is_overlap]
    num_normal_hl = df[(df["run_type"] == "numeric") & is_normal & is_overlap]
    num_outlier_nohl = df[(df["run_type"] == "numeric") & is_outlier & ~is_overlap]
    num_outlier_hl = df[(df["run_type"] == "numeric") & is_outlier & is_overlap]

    # xr tested — triangle
    if len(xr_normal) > 0:
        ax.scatter(xr_normal.index, xr_normal["spe_gain"],
                   c=COLOR_XR, marker="^", s=50, zorder=3, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"xr tested (n={len(xr_normal)})")
    if len(xr_outlier) > 0:
        ax.scatter(xr_outlier.index, xr_outlier["spe_gain"],
                   c=COLOR_XR, marker="^", s=80, zorder=5, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"xr tested outlier (n={len(xr_outlier)})")

    # westlake tested normal — circle (non-overlap)
    if len(num_normal_nohl) > 0:
        ax.scatter(num_normal_nohl.index, num_normal_nohl["spe_gain"],
                   c=COLOR_NUM, marker="o", s=40, zorder=2, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"westlake tested (n={len(num_normal_nohl)})")
    # westlake tested normal — overlap (紫色空心圆)
    if len(num_normal_hl) > 0:
        ax.scatter(num_normal_hl.index, num_normal_hl["spe_gain"],
                   c=COLOR_OVERLAP, marker="D", s=60, zorder=6, alpha=0.9,
                   edgecolors=COLOR_OVERLAP, linewidths=1.5,
                   label=f"overlap xr+westlake (n={len(num_normal_hl)})")
    # westlake tested outlier — non-overlap
    if len(num_outlier_nohl) > 0:
        ax.scatter(num_outlier_nohl.index, num_outlier_nohl["spe_gain"],
                   c=COLOR_NUM, marker="o", s=70, zorder=4, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"westlake tested outlier (n={len(num_outlier_nohl)})")
    # westlake tested outlier — overlap
    if len(num_outlier_hl) > 0:
        ax.scatter(num_outlier_hl.index, num_outlier_hl["spe_gain"],
                   c=COLOR_OVERLAP, marker="D", s=80, zorder=7, alpha=0.9,
                   edgecolors=COLOR_OVERLAP, linewidths=1.5,
                   label=f"overlap outlier (n={len(num_outlier_hl)})")

    # Annotate outliers (both overlap and non-overlap)
    outlier_indices = df[is_outlier].index
    for i in outlier_indices:
        val = df.loc[i, "spe_gain"]
        pid = df.loc[i, "pmt_id"]
        color = COLOR_OVERLAP if df.loc[i, "pmt_id"] in overlap_pmts else COLOR_OUTLIER
        ax.annotate(pid, (i, val), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7, color=color, fontweight="bold")

    # Median line
    ax.axhline(median_val, color=COLOR_MEDIAN, linestyle="--", linewidth=1.5,
               label=f"Median: {median_val:.2f}", zorder=1)

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("Gain [e$^{-}$]", fontsize=12)
    ax.set_title("SPE Gain vs PMT ID  (◈ = overlap xr+westlake)", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(df) - 0.5)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    overlap_pmts = _load_overlap_pmts()
    print(f"Overlap PMTs loaded: {len(overlap_pmts)}")
    df = load_data(DB_PATH)
    print(f"Loaded {len(df)} records (hv ≤ 800 V) with SPE gain")
    print(f"  xr tested:        {len(df[df['run_type'] == 'xr'])}")
    print(f"  westlake tested:  {len(df[df['run_type'] == 'numeric'])}")
    print(f"  Overlap PMTs:     {len(df[df['pmt_id'].isin(overlap_pmts)])}")
    print(f"  Gain range:       {df['spe_gain'].min():.2f} – {df['spe_gain'].max():.2f}")
    print(f"  Gain mean:        {df['spe_gain'].mean():.2f}")
    print(f"  Gain median:      {df['spe_gain'].median():.2f}")
    print(f"  Gain std:         {df['spe_gain'].std():.2f}")

    out_hist = os.path.join(FIGS_DIR, "gain_histogram.png")
    out_scatter = os.path.join(FIGS_DIR, "gain_scatter.png")

    plot_histogram(df, out_hist)
    plot_scatter(df, out_scatter, overlap_pmts)

    print("Done.")


if __name__ == "__main__":
    main()
