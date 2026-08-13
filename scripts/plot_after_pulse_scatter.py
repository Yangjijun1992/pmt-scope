"""plot_after_pulse_scatter.py — 后脉冲概率（After-Pulse Probability）散点图

vs PMT ID 散点图：
     - 数值 ×100 换算为 APP[%]
     - xr* run_id: 绿色三角形 (^)
     - 纯数字 run_id: 蓝色圆形 (o)
     - APP[%] > 5%: 红色标注
     - overlap PMT: 紫色空心菱形 (◇)

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/after_pulse_scatter.png
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
APP_THRESHOLD_PCT = 5.0
PCT_SCALE = 100.0

COLOR_XR = "#2CA02C"        # green: USTC (科大)
COLOR_NUM = "#2B6FB3"       # blue: Westlake (西湖)
COLOR_RED = "#D62728"
COLOR_THRESHOLD = "#333333"


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
               AVG(after_pulse_probability) AS after_pulse_probability
        FROM measurements
        WHERE after_pulse_probability IS NOT NULL
        GROUP BY pmt_id, channel_id, run_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["run_type"] = df["run_id"].apply(
        lambda x: "xr" if bool(re.match(r"^xr", str(x))) else "numeric"
    )

    df["after_pulse_pct"] = df["after_pulse_probability"] * PCT_SCALE

    df.sort_values(["pmt_id", "channel_id", "run_type"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def plot_scatter(df: pd.DataFrame, out_path: str, overlap_pmts: set):
    is_overlap = df["pmt_id"].isin(overlap_pmts)
    is_above = df["after_pulse_pct"] > APP_THRESHOLD_PCT

    fig, ax = plt.subplots(figsize=(18, 6))

    xr_below = df[(df["run_type"] == "xr") & ~is_above]
    xr_above = df[(df["run_type"] == "xr") & is_above]
    num_below = df[(df["run_type"] == "numeric") & ~is_above]
    num_above = df[(df["run_type"] == "numeric") & is_above]

    if len(xr_below) > 0:
        ax.scatter(xr_below.index, xr_below["after_pulse_pct"],
                   c=COLOR_XR, marker="^", s=55, zorder=4, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"USTC APP ≤ {APP_THRESHOLD_PCT:.0f}% (n={len(xr_below)})")
    if len(xr_above) > 0:
        ax.scatter(xr_above.index, xr_above["after_pulse_pct"],
                   c=COLOR_XR, marker="^", s=55, zorder=4, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"USTC APP > {APP_THRESHOLD_PCT:.0f}% (n={len(xr_above)})")

    if len(num_below) > 0:
        ax.scatter(num_below.index, num_below["after_pulse_pct"],
                   c=COLOR_NUM, marker="o", s=40, zorder=3, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"Westlake APP ≤ {APP_THRESHOLD_PCT:.0f}% (n={len(num_below)})")
    if len(num_above) > 0:
        ax.scatter(num_above.index, num_above["after_pulse_pct"],
                   c=COLOR_NUM, marker="o", s=40, zorder=3, alpha=0.85,
                   edgecolors="white", linewidths=0.3,
                   label=f"Westlake APP > {APP_THRESHOLD_PCT:.0f}% (n={len(num_above)})")

    overlap_df = df[is_overlap]

    for pid, group in overlap_df.groupby("pmt_id"):
        xr_group = group[group["run_type"] == "xr"]
        num_group = group[group["run_type"] == "numeric"]
        if len(xr_group) > 0 and len(num_group) > 0:
            xr_x = np.mean(xr_group.index)
            num_x = np.mean(num_group.index)
            xr_y = xr_group["after_pulse_pct"].mean()
            num_y = num_group["after_pulse_pct"].mean()
            ax.plot([xr_x, num_x], [xr_y, num_y],
                    color="#8E44AD", linestyle="--", linewidth=1.2,
                    alpha=0.7, zorder=1.5, solid_capstyle="round")

    if len(overlap_df) > 0:
        ax.scatter(overlap_df.index, overlap_df["after_pulse_pct"],
                   c="none", marker="o", s=110, zorder=6, linewidths=1.6,
                   edgecolors="#E91E63", alpha=0.9)

    if len(overlap_df) > 0:
        ax.plot([], [], "--", color="#8E44AD", linewidth=1.2, alpha=0.7,
                label="overlap: USTC + Westlake")
        ax.scatter([], [], c="none", marker="o", s=110, linewidths=1.6,
                   edgecolors="#E91E63", alpha=0.9,
                   label=f"overlap ring (n={len(overlap_df)})")

    above_df = df[is_above]
    for i in above_df.index:
        val = df.loc[i, "after_pulse_pct"]
        pid = df.loc[i, "pmt_id"]
        color = COLOR_NUM if df.loc[i, "run_type"] == "numeric" else COLOR_XR
        ax.annotate(pid, (i, val), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7, color=color, fontweight="bold")

    ax.axhline(APP_THRESHOLD_PCT, color=COLOR_THRESHOLD, linestyle="--", linewidth=1.5,
               label=f"Threshold: {APP_THRESHOLD_PCT:.0f}% ({APP_THRESHOLD_PCT / PCT_SCALE:g})", zorder=1)

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["pmt_id"], rotation=90, fontsize=5)
    ax.set_xlabel("PMT ID", fontsize=12)
    ax.set_ylabel("After-Pulse Probability [%]", fontsize=12)
    ax.set_title("After-Pulse Probability vs PMT ID  (▲ = USTC, ● = Westlake)", fontsize=14, fontweight="bold")
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
    print(f"Loaded {len(df)} records with after-pulse probability")
    print(f"  xr tested:        {len(df[df['run_type'] == 'xr'])}")
    print(f"  westlake tested:  {len(df[df['run_type'] == 'numeric'])}")
    print(f"  APP[%] range: {df['after_pulse_pct'].min():.2f}% – {df['after_pulse_pct'].max():.2f}%")
    print(f"  APP[%] mean:  {df['after_pulse_pct'].mean():.2f}%")
    print(f"  APP[%] median:{df['after_pulse_pct'].median():.2f}%")
    print(f"  Overlap PMTs:   {len(df[df['pmt_id'].isin(overlap_pmts)])}")

    out_scatter = os.path.join(FIGS_DIR, "after_pulse_scatter.png")
    plot_scatter(df, out_scatter, overlap_pmts)

    print("Done.")


if __name__ == "__main__":
    main()
