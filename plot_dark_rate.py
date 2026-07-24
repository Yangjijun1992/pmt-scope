"""plot_dark_rate.py — 暗计数率（Dark Count Rate）分布图

图1: 直方图，按频率区间着色（蓝/橙红/红）
图2: vs PMT ID 散点图，三种形状，中位数虚线，>2000Hz 标注 pmt_id

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/dark_rate_histogram.png, figs/dark_rate_scatter.png
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "pmt-data-client", "data", "pmt_data.db")
FIGS_DIR = os.path.join(os.path.dirname(__file__), "figs")
DCR_MIN, DCR_MAX = 50.0, 5000.0
THRESHOLD_LOW = 1000.0
THRESHOLD_HIGH = 2000.0

COLOR_LOW = "#2B6FB3"       # blue
COLOR_MID = "#E8652D"       # orange-red
COLOR_HIGH = "#D62728"      # red
COLOR_MEDIAN = "#333333"


def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               AVG(dark_count_rate) AS dark_count_rate
        FROM measurements
        WHERE dark_count_rate IS NOT NULL
        GROUP BY pmt_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df = df[(df["dark_count_rate"] >= DCR_MIN) & (df["dark_count_rate"] <= DCR_MAX)].copy()
    df.sort_values("pmt_id", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def split_groups(df: pd.DataFrame):
    low = df[df["dark_count_rate"] < THRESHOLD_LOW].copy()
    mid = df[(df["dark_count_rate"] >= THRESHOLD_LOW) & (df["dark_count_rate"] <= THRESHOLD_HIGH)].copy()
    high = df[df["dark_count_rate"] > THRESHOLD_HIGH].copy()
    return low, mid, high


def plot_histogram(df: pd.DataFrame, out_path: str):
    low, mid, high = split_groups(df)
    median_val = df["dark_count_rate"].median()

    fig, ax = plt.subplots(figsize=(10, 6))

    bins = np.histogram_bin_edges(df["dark_count_rate"], bins="auto")
    ax.hist(low["dark_count_rate"], bins=bins, color=COLOR_LOW, alpha=0.85,
            label=f"< {THRESHOLD_LOW:.0f} Hz  (n={len(low)})")
    ax.hist(mid["dark_count_rate"], bins=bins, color=COLOR_MID, alpha=0.85,
            label=f"{THRESHOLD_LOW:.0f}–{THRESHOLD_HIGH:.0f} Hz  (n={len(mid)})")
    ax.hist(high["dark_count_rate"], bins=bins, color=COLOR_HIGH, alpha=0.85,
            label=f"> {THRESHOLD_HIGH:.0f} Hz  (n={len(high)})")

    ax.axvline(THRESHOLD_LOW, color=COLOR_MEDIAN, linestyle="--", linewidth=3.0,
               label=f"Threshold: {THRESHOLD_LOW:.0f} Hz")

    ax.set_xlabel("Dark Count Rate [Hz]", fontsize=14, x=0.94, ha="right")
    ax.set_ylabel("Counts", fontsize=14)
    ax.set_title("Dark Count Rate Distribution", fontsize=16, fontweight="bold")
    ax.set_xlim(DCR_MIN, DCR_MAX)
    ax.tick_params(axis="both", labelsize=12)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def plot_scatter(df: pd.DataFrame, out_path: str):
    low, mid, high = split_groups(df)
    median_val = df["dark_count_rate"].median()

    fig, ax = plt.subplots(figsize=(18, 6))

    x_pos = range(len(df))
    df_sorted = df.reset_index(drop=True)

    # Build position mappings for each group
    group_mask = {
        "low": df_sorted["dark_count_rate"] < THRESHOLD_LOW,
        "mid": (df_sorted["dark_count_rate"] >= THRESHOLD_LOW) & (df_sorted["dark_count_rate"] <= THRESHOLD_HIGH),
        "high": df_sorted["dark_count_rate"] > THRESHOLD_HIGH,
    }

    for mask, color, marker, label, s, z in [
        (group_mask["low"], COLOR_LOW, "o", f"< {THRESHOLD_LOW:.0f} Hz", 40, 3),
        (group_mask["mid"], COLOR_MID, "^", f"{THRESHOLD_LOW:.0f}–{THRESHOLD_HIGH:.0f} Hz", 50, 4),
        (group_mask["high"], COLOR_HIGH, "x", f"> {THRESHOLD_HIGH:.0f} Hz", 70, 5),
    ]:
        indices = [i for i, m in enumerate(mask) if m]
        x_vals = [i for i in indices]
        y_vals = df_sorted.loc[indices, "dark_count_rate"].values
        ax.scatter(x_vals, y_vals, c=color, marker=marker, s=s, zorder=z,
                   label=label, linewidths=0.8)

    # Annotate high-DCR PMTs (>2000 Hz)
    high_indices = [i for i, m in enumerate(group_mask["high"]) if m]
    for i in high_indices:
        val = df_sorted.loc[i, "dark_count_rate"]
        pid = df_sorted.loc[i, "pmt_id"]
        ax.annotate(pid, (i, val), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7, color=COLOR_HIGH, fontweight="bold")

    # Median line
    ax.axhline(median_val, color=COLOR_MEDIAN, linestyle="--", linewidth=1.5,
               label=f"Median: {median_val:.0f} Hz", zorder=1)

    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(df_sorted["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("Dark Count Rate [Hz]", fontsize=12)
    ax.set_title("Dark Count Rate vs PMT ID", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(df_sorted) - 0.5)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    df = load_data(DB_PATH)
    print(f"Loaded {len(df)} PMTs with dark count rate in [{DCR_MIN}, {DCR_MAX}] Hz")

    out_hist = os.path.join(FIGS_DIR, "dark_rate_histogram.png")
    out_scatter = os.path.join(FIGS_DIR, "dark_rate_scatter.png")

    plot_histogram(df, out_hist)
    plot_scatter(df, out_scatter)

    print("Done.")


if __name__ == "__main__":
    main()
