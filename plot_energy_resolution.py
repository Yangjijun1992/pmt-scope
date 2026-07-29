"""plot_energy_resolution.py — 能量分辨率（Energy Resolution）分布图

图1: 直方图，0.5 分割线，legend 标注 <0.5 / >=0.5 数量
图2: vs PMT ID 散点图
     - xr* run_id: 方块 marker
     - 纯数字 run_id: 圆形 marker
     - energy_res >= 0.5: 红色
     - energy_res < 0.5: 蓝色

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/energy_resolution_histogram.png, figs/energy_resolution_scatter.png
"""

import os
import re
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pmt-data-client", "data", "pmt_data.db")
FIGS_DIR = os.path.join(os.path.dirname(__file__), "figs")
ER_BINS = 20
ER_X_MIN, ER_X_MAX = 0.0, 1.0
ER_THRESHOLD = 0.5

COLOR_BLUE = "#2B6FB3"
COLOR_RED = "#D62728"
COLOR_THRESHOLD = "#333333"


def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               channel_id,
               run_id,
               AVG(energy_resolution) AS energy_resolution
        FROM measurements
        WHERE energy_resolution IS NOT NULL
        GROUP BY pmt_id, channel_id, run_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["run_type"] = df["run_id"].apply(
        lambda x: "xr" if bool(re.match(r"^xr", str(x))) else "numeric"
    )

    df.sort_values(["pmt_id", "channel_id", "run_type"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def plot_histogram(df: pd.DataFrame, out_path: str):
    below = df[df["energy_resolution"] < ER_THRESHOLD]
    above = df[df["energy_resolution"] >= ER_THRESHOLD]
    n_below = len(below)
    n_above = len(above)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(df["energy_resolution"], bins=ER_BINS, color=COLOR_BLUE, alpha=0.85,
            edgecolor="white", linewidth=0.8)

    ax.axvline(ER_THRESHOLD, color=COLOR_RED, linestyle="--", linewidth=3.0,
               label=f"Threshold: {ER_THRESHOLD}")

    # Add count legend entries
    ax.plot([], [], " ", label=f"< {ER_THRESHOLD}: {n_below} channels")
    ax.plot([], [], " ", label=f"≥ {ER_THRESHOLD}: {n_above} channels")

    ax.set_xlabel("Energy Resolution", fontsize=16, x=0.94, ha="right")
    ax.set_ylabel("Counts", fontsize=16)
    ax.set_title("Energy Resolution Distribution", fontsize=18, fontweight="bold")
    ax.set_xlim(ER_X_MIN, ER_X_MAX)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(loc="upper right", fontsize=12)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def plot_scatter(df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(18, 6))

    xr_below = df[(df["run_type"] == "xr") & (df["energy_resolution"] < ER_THRESHOLD)]
    xr_above = df[(df["run_type"] == "xr") & (df["energy_resolution"] >= ER_THRESHOLD)]
    num_below = df[(df["run_type"] == "numeric") & (df["energy_resolution"] < ER_THRESHOLD)]
    num_above = df[(df["run_type"] == "numeric") & (df["energy_resolution"] >= ER_THRESHOLD)]

    # xr run_id — square marker
    if len(xr_below) > 0:
        ax.scatter(xr_below.index, xr_below["energy_resolution"],
                   c=COLOR_BLUE, marker="s", s=50, zorder=4, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"xr tested (n={len(xr_below)})")
    if len(xr_above) > 0:
        ax.scatter(xr_above.index, xr_above["energy_resolution"],
                   c=COLOR_RED, marker="s", s=50, zorder=4, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"xr tested (n={len(xr_above)})")

    # numeric run_id — circle marker
    if len(num_below) > 0:
        ax.scatter(num_below.index, num_below["energy_resolution"],
                   c=COLOR_BLUE, marker="o", s=40, zorder=3, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"westlake tested (n={len(num_below)})")
    if len(num_above) > 0:
        ax.scatter(num_above.index, num_above["energy_resolution"],
                   c=COLOR_RED, marker="o", s=40, zorder=3, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"westlake tested (n={len(num_above)})")

    # Threshold line
    ax.axhline(ER_THRESHOLD, color=COLOR_THRESHOLD, linestyle="--", linewidth=1.5,
               label=f"Threshold: {ER_THRESHOLD}", zorder=1)

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("Energy Resolution", fontsize=12)
    ax.set_title("Energy Resolution vs PMT ID", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(df) - 0.5)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    df = load_data(DB_PATH)
    print(f"Loaded {len(df)} records (pmt_id + channel_id + run_id) with energy resolution")
    print(f"  ER range:     {df['energy_resolution'].min():.4f} – {df['energy_resolution'].max():.4f}")
    print(f"  ER mean:      {df['energy_resolution'].mean():.4f}")
    print(f"  ER median:    {df['energy_resolution'].median():.4f}")
    print(f"  ER std:       {df['energy_resolution'].std():.4f}")
    print(f"  < 0.5 count:  {len(df[df['energy_resolution'] < ER_THRESHOLD])}")
    print(f"  >= 0.5 count: {len(df[df['energy_resolution'] >= ER_THRESHOLD])}")
    print(f"  xr* runs:     {len(df[df['run_type'] == 'xr'])}")
    print(f"  numeric runs: {len(df[df['run_type'] == 'numeric'])}")

    out_hist = os.path.join(FIGS_DIR, "energy_resolution_histogram.png")
    out_scatter = os.path.join(FIGS_DIR, "energy_resolution_scatter.png")

    plot_histogram(df, out_hist)
    plot_scatter(df, out_scatter)

    print("Done.")


if __name__ == "__main__":
    main()
