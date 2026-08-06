"""plot_dark_rate.py — 暗计数率（Dark Count Rate）分布图

图1: 直方图，按频率区间着色（蓝/橙红/红）
图2: vs PMT ID 散点图
     - xr* run_id: 方块 (s)
     - 纯数字 run_id: 圆形 (o), 同一 pmt_id 只保留 DCR 最小值
     - < 1000 Hz: 蓝色; 1000–2000 Hz: 橙色; > 2000 Hz: 红色
     - overlap PMT: 紫色空心菱形 (◇)

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/dark_rate_histogram.png, figs/dark_rate_scatter.png
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
DCR_MIN, DCR_MAX = 50.0, 5000.0
THRESHOLD_LOW = 1000.0
THRESHOLD_HIGH = 2000.0

COLOR_LOW = "#2B6FB3"       # blue
COLOR_MID = "#E8652D"       # orange
COLOR_HIGH = "#D62728"      # red
COLOR_MEDIAN = "#333333"
COLOR_XR = "#2CA02C"        # green: USTC (科大)
COLOR_NUM = "#2B6FB3"       # blue: Westlake (西湖)


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
               AVG(dark_count_rate) AS dark_count_rate
        FROM measurements
        WHERE dark_count_rate IS NOT NULL
        GROUP BY pmt_id, channel_id, run_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["run_type"] = df["run_id"].apply(
        lambda x: "xr" if bool(re.match(r"^xr", str(x))) else "numeric"
    )

    df = df[(df["dark_count_rate"] >= DCR_MIN) & (df["dark_count_rate"] <= DCR_MAX)].copy()

    # For westlake tested (numeric), keep only the minimum DCR per pmt_id
    num_df = df[df["run_type"] == "numeric"].copy()
    xr_df = df[df["run_type"] == "xr"].copy()

    num_df = num_df.loc[num_df.groupby("pmt_id")["dark_count_rate"].idxmin()].copy()

    df = pd.concat([xr_df, num_df], ignore_index=True)

    df.sort_values(["pmt_id", "channel_id", "run_type"], inplace=True)
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


def plot_scatter(df: pd.DataFrame, out_path: str, overlap_pmts: set):
    median_val = df["dark_count_rate"].median()

    is_overlap = df["pmt_id"].isin(overlap_pmts)

    fig, ax = plt.subplots(figsize=(18, 6))

    low_mask = df["dark_count_rate"] < THRESHOLD_LOW
    mid_mask = (df["dark_count_rate"] >= THRESHOLD_LOW) & (df["dark_count_rate"] <= THRESHOLD_HIGH)
    high_mask = df["dark_count_rate"] > THRESHOLD_HIGH

    # Plot by DCR range, with USTC (green triangle) / Westlake (blue circle)
    for mask, color, dcr_label in [
        (low_mask, COLOR_LOW, f"< {THRESHOLD_LOW:.0f} Hz"),
        (mid_mask, COLOR_MID, f"{THRESHOLD_LOW:.0f}–{THRESHOLD_HIGH:.0f} Hz"),
        (high_mask, COLOR_HIGH, f"> {THRESHOLD_HIGH:.0f} Hz"),
    ]:
        subset = df[mask]
        xr_sub = subset[subset["run_type"] == "xr"]
        num_sub = subset[subset["run_type"] == "numeric"]

        if len(xr_sub) > 0:
            ax.scatter(xr_sub.index, xr_sub["dark_count_rate"],
                       c=COLOR_XR, marker="^", s=55, zorder=4, alpha=0.85,
                       edgecolors="white", linewidths=0.3,
                       label=f"{dcr_label} – USTC (n={len(xr_sub)})")
        if len(num_sub) > 0:
            ax.scatter(num_sub.index, num_sub["dark_count_rate"],
                       c=COLOR_NUM, marker="o", s=40, zorder=3, alpha=0.85,
                       edgecolors="white", linewidths=0.3,
                       label=f"{dcr_label} – Westlake (n={len(num_sub)})")

    # Mark overlap PMTs (tested at both USTC and Westlake)
    overlap_df = df[is_overlap]

    # Draw one dashed vertical connector between USTC and Westlake representative
    # points (mean of xr points and mean of numeric points) when both are present.
    for pid, group in overlap_df.groupby("pmt_id"):
        xr_group = group[group["run_type"] == "xr"]
        num_group = group[group["run_type"] == "numeric"]
        if len(xr_group) > 0 and len(num_group) > 0:
            xr_x = np.mean(xr_group.index)
            num_x = np.mean(num_group.index)
            xr_y = xr_group["dark_count_rate"].mean()
            num_y = num_group["dark_count_rate"].mean()
            ax.plot([xr_x, num_x], [xr_y, num_y],
                    color="#8E44AD", linestyle="--", linewidth=1.2,
                    alpha=0.7, zorder=1.5, solid_capstyle="round")

    # Ring every overlap point (whether 1 or 2 present) so overlap PMTs are clearly
    # identified even when only a single site's point survives filtering.
    if len(overlap_df) > 0:
        ax.scatter(overlap_df.index, overlap_df["dark_count_rate"],
                   c="none", marker="o", s=110, zorder=6, linewidths=1.6,
                   edgecolors="#E91E63", alpha=0.9)
        # (legend entry below)

    # Annotate high-DCR PMTs (>2000 Hz)
    high_subset = df[high_mask]
    for i in high_subset.index:
        val = df.loc[i, "dark_count_rate"]
        pid = df.loc[i, "pmt_id"]
        color = COLOR_NUM if df.loc[i, "run_type"] == "numeric" else COLOR_XR
        ax.annotate(pid, (i, val), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7, color=color, fontweight="bold")

    # Legend entry for the overlap identifier(s)
    if len(overlap_df) > 0:
        ax.plot([], [], "--", color="#8E44AD", linewidth=1.2, alpha=0.7,
                label="overlap: USTC + Westlake")
        ax.scatter([], [], c="none", marker="o", s=110, linewidths=1.6,
                   edgecolors="#E91E63", alpha=0.9,
                   label=f"overlap ring (n={len(overlap_df)})")

    # Threshold line
    ax.axhline(THRESHOLD_LOW, color=COLOR_MEDIAN, linestyle="--", linewidth=1.5,
               label=f"Threshold: {THRESHOLD_LOW:.0f} Hz", zorder=1)

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("Dark Count Rate [Hz]", fontsize=12)
    ax.set_title("Dark Count Rate vs PMT ID  (▲ = USTC, ● = Westlake)", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=7)
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
    print(f"Loaded {len(df)} records with dark count rate in [{DCR_MIN}, {DCR_MAX}] Hz")
    print(f"  xr tested:        {len(df[df['run_type'] == 'xr'])}")
    print(f"  westlake tested:  {len(df[df['run_type'] == 'numeric'])}")
    print(f"  Overlap PMTs:     {len(df[df['pmt_id'].isin(overlap_pmts)])}")
    print(f"  < 1000 Hz:        {len(df[df['dark_count_rate'] < THRESHOLD_LOW])}")
    print(f"  1000–2000 Hz:     {len(df[(df['dark_count_rate'] >= THRESHOLD_LOW) & (df['dark_count_rate'] <= THRESHOLD_HIGH)])}")
    print(f"  > 2000 Hz:        {len(df[df['dark_count_rate'] > THRESHOLD_HIGH])}")

    out_hist = os.path.join(FIGS_DIR, "dark_rate_histogram.png")
    out_scatter = os.path.join(FIGS_DIR, "dark_rate_scatter.png")

    plot_histogram(df, out_hist)
    plot_scatter(df, out_scatter, overlap_pmts)

    print("Done.")


if __name__ == "__main__":
    main()
