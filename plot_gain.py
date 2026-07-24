"""plot_gain.py — SPE Gain 独立绘图脚本

图1: 直方图，bins=35，x_range=[-5, 30]
图2: vs PMT ID 散点图，中位数虚线，3σ 离群点标注

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/gain_histogram.png, figs/gain_scatter.png
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pmt-data-client", "data", "pmt_data.db")
FIGS_DIR = os.path.join(os.path.dirname(__file__), "figs")
GAIN_X_MIN, GAIN_X_MAX = 0.0, 3e7
GAIN_BINS = 30
SIGMA_MULTIPLIER = 3.0

COLOR_BAR = "#4C78A8"
COLOR_MEDIAN = "#333333"
COLOR_SCATTER = "#2B6FB3"
COLOR_OUTLIER = "#D62728"


def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               AVG(spe_gain) AS spe_gain
        FROM measurements
        WHERE spe_gain IS NOT NULL
        GROUP BY pmt_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df["spe_gain"] = df["spe_gain"] * 1e6
    df.sort_values("pmt_id", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def plot_histogram(df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(df["spe_gain"], bins=GAIN_BINS, color=COLOR_BAR, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    ax.set_xlabel("Gain [e$^{-}$]", fontsize=16, x=0.94, ha="right")
    ax.set_ylabel("Counts", fontsize=16)
    ax.set_title("SPE Gain Distribution", fontsize=18, fontweight="bold")
    ax.set_xlim(GAIN_X_MIN, GAIN_X_MAX)
    ax.tick_params(axis="both", labelsize=14)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def plot_scatter(df: pd.DataFrame, out_path: str):
    median_val = df["spe_gain"].median()
    mean_val = df["spe_gain"].mean()
    std_val = df["spe_gain"].std()
    lower_bound = mean_val - SIGMA_MULTIPLIER * std_val
    upper_bound = mean_val + SIGMA_MULTIPLIER * std_val

    is_outlier = (df["spe_gain"] < lower_bound) | (df["spe_gain"] > upper_bound)
    is_normal = ~is_outlier

    fig, ax = plt.subplots(figsize=(18, 6))

    x_pos = range(len(df))

    # Normal points
    normal_mask = is_normal.values
    normal_indices = [i for i, m in enumerate(normal_mask) if m]
    ax.scatter(normal_indices, df.loc[normal_indices, "spe_gain"],
               c=COLOR_SCATTER, marker="o", s=35, zorder=2, label="Normal")

    # Outlier points
    outlier_mask = is_outlier.values
    outlier_indices = [i for i, m in enumerate(outlier_mask) if m]
    if outlier_indices:
        ax.scatter(outlier_indices, df.loc[outlier_indices, "spe_gain"],
                   c=COLOR_OUTLIER, marker="x", s=80, zorder=5, linewidths=1.5,
                   label=f"Outlier ($3\\sigma$)")

    # Annotate outliers
    for i in outlier_indices:
        val = df.loc[i, "spe_gain"]
        pid = df.loc[i, "pmt_id"]
        ax.annotate(pid, (i, val), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7, color=COLOR_OUTLIER, fontweight="bold")

    # Median line
    ax.axhline(median_val, color=COLOR_MEDIAN, linestyle="--", linewidth=1.5,
               label=f"Median: {median_val:.2e}", zorder=1)

    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(df["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("Gain [e$^{-}$]", fontsize=12)
    ax.set_title("SPE Gain vs PMT ID", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(df) - 0.5)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    df = load_data(DB_PATH)
    print(f"Loaded {len(df)} PMTs with SPE gain")
    print(f"  Gain range:  {df['spe_gain'].min():.2e} – {df['spe_gain'].max():.2e}")
    print(f"  Gain mean:   {df['spe_gain'].mean():.2e}")
    print(f"  Gain median: {df['spe_gain'].median():.2e}")
    print(f"  Gain std:    {df['spe_gain'].std():.2e}")

    out_hist = os.path.join(FIGS_DIR, "gain_histogram.png")
    out_scatter = os.path.join(FIGS_DIR, "gain_scatter.png")

    plot_histogram(df, out_hist)
    plot_scatter(df, out_scatter)

    print("Done.")


if __name__ == "__main__":
    main()
