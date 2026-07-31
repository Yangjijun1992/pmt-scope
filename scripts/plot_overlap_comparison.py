"""plot_overlap_comparison.py — 重复 PMT 两次测试对比散点图

对 docs/overlap_pmt_ids.csv 中的 PMT，对比 USTC (xr) 与 Westlake (numeric) 的：
  - Dark Count Rate
  - SPE Gain (hv ≤ 800V)
  - Energy Resolution

每个 PMT 用竖线连接两次测量结果，不同形状/颜色区分测试地点：
  - USTC (xr) : 红色三角形 ▲
  - Westlake   : 蓝色圆形   ●

数据源: ../../pmt-data-client/data/pmt_data.db
输出: figs/overlap_dcr_comparison.png, figs/overlap_gain_comparison.png, figs/overlap_er_comparison.png
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

COLOR_XR = "#D62728"
COLOR_WL = "#2B6FB3"
COLOR_LINE = "#AAAAAA"


def _load_overlap_pmts() -> set:
    path = os.path.join(os.path.dirname(__file__), "..", "docs", "overlap_pmt_ids.csv")
    if os.path.exists(path):
        try:
            overlap_df = pd.read_csv(path)
            return set(overlap_df["pmt_id"].dropna().tolist())
        except Exception:
            return set()
    return set()


def _load_and_aggregate(db_path: str, column: str, hv_filter: bool = False) -> pd.DataFrame:
    """按 (pmt_id, run_id) 聚合指定列，按 pmt_id 分别取 xr/numeric 均值。"""
    conn = sqlite3.connect(db_path)

    if hv_filter and column == "spe_gain":
        query = f"""
            SELECT pmt_id, run_id,
                   AVG({column}) AS {column}
            FROM measurements
            WHERE {column} IS NOT NULL AND hv <= 800
            GROUP BY pmt_id, run_id
        """
    else:
        query = f"""
            SELECT pmt_id, run_id,
                   AVG({column}) AS {column}
            FROM measurements
            WHERE {column} IS NOT NULL
            GROUP BY pmt_id, run_id
        """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["run_type"] = df["run_id"].apply(
        lambda x: "xr" if bool(re.match(r"^xr", str(x))) else "numeric"
    )

    agg = df.groupby(["pmt_id", "run_type"])[column].mean().unstack()
    agg = agg.dropna(subset=["xr", "numeric"], how="all")
    return agg


def _plot_comparison(agg: pd.DataFrame, column: str, out_path: str,
                     ylabel: str, title: str, threshold: float = None):
    """绘制单参数对比散点图。"""
    overlap_pmts = _load_overlap_pmts()
    pmt_ids = sorted(agg.index)

    fig, ax = plt.subplots(figsize=(14, 6))

    for i, pid in enumerate(pmt_ids):
        if "xr" in agg.columns and pid in agg.index:
            xr_val = agg.loc[pid, "xr"]
        else:
            xr_val = np.nan
        if "numeric" in agg.columns and pid in agg.index:
            num_val = agg.loc[pid, "numeric"]
        else:
            num_val = np.nan

        if pd.notna(xr_val) and pd.notna(num_val):
            ax.plot([i, i], [xr_val, num_val], color=COLOR_LINE, linewidth=1,
                    linestyle=":", zorder=1)

        if pd.notna(xr_val):
            ax.scatter([i], [xr_val], c=COLOR_XR, marker="^", s=80, zorder=3,
                       edgecolors="white", linewidths=0.5, label="USTC (xr)" if i == 0 else "")

        if pd.notna(num_val):
            ax.scatter([i], [num_val], c=COLOR_WL, marker="o", s=80, zorder=2,
                       edgecolors="white", linewidths=0.5, label="Westlake" if i == 0 else "")

    if threshold is not None:
        ax.axhline(threshold, color=COLOR_XR, linestyle="--", linewidth=2,
                   alpha=0.6, label=f"Threshold: {threshold}")

    ax.set_xticks(range(len(pmt_ids)))
    ax.set_xticklabels(pmt_ids, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(pmt_ids) - 0.5)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    overlap_pmts = _load_overlap_pmts()
    print(f"Overlap PMTs loaded: {len(overlap_pmts)}")
    print(f"  PMT IDs: {', '.join(sorted(overlap_pmts))}")

    # ── Dark Count Rate ──
    dcr_agg = _load_and_aggregate(DB_PATH, "dark_count_rate")
    dcr_agg = dcr_agg[dcr_agg.index.isin(overlap_pmts)]
    print(f"\n--- Dark Count Rate ---")
    print(f"  PMTs with both measurements: {dcr_agg.dropna().shape[0]}")
    if dcr_agg.dropna().shape[0] > 0:
        _plot_comparison(
            dcr_agg, "dark_count_rate",
            os.path.join(FIGS_DIR, "overlap_dcr_comparison.png"),
            ylabel="Dark Count Rate [Hz]",
            title="Overlap PMT Dark Count Rate: USTC vs Westlake",
        )

    # ── SPE Gain (hv ≤ 800V) ──
    gain_agg = _load_and_aggregate(DB_PATH, "spe_gain", hv_filter=True)
    gain_agg = gain_agg[gain_agg.index.isin(overlap_pmts)]
    print(f"\n--- SPE Gain (hv ≤ 800V) ---")
    print(f"  PMTs with both measurements: {gain_agg.dropna().shape[0]}")
    if gain_agg.dropna().shape[0] > 0:
        _plot_comparison(
            gain_agg, "spe_gain",
            os.path.join(FIGS_DIR, "overlap_gain_comparison.png"),
            ylabel="Gain [1.E6 e⁻]",
            title="Overlap PMT SPE Gain (hv ≤ 800V): USTC vs Westlake",
        )

    # ── Energy Resolution ──
    er_agg = _load_and_aggregate(DB_PATH, "energy_resolution")
    er_agg = er_agg[er_agg.index.isin(overlap_pmts)]
    print(f"\n--- Energy Resolution ---")
    print(f"  PMTs with both measurements: {er_agg.dropna().shape[0]}")
    if er_agg.dropna().shape[0] > 0:
        _plot_comparison(
            er_agg, "energy_resolution",
            os.path.join(FIGS_DIR, "overlap_er_comparison.png"),
            ylabel="Energy Resolution",
            title="Overlap PMT Energy Resolution: USTC vs Westlake",
            threshold=0.5,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
