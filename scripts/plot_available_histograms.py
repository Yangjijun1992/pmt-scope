"""plot_available_histograms.py — 可用候选 PMT（扣除占用后）四个参数直方图

对每个参数（DCR、Gain、ER、APP）绘制一张直方图，标注均值/中位数。
数据源: docs/candidates_available.csv（已扣除 supplemental_list 中占用 PMT）
输出: figs/available_<param>_histogram.png
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "candidates_available.csv")
FIGS_DIR = os.path.join(ROOT, "figs")

COLOR_BAR = "#4C78A8"
COLOR_MEDIAN = "#D62728"
COLOR_MEAN = "#9467BD"

# (列名, 图题, xlabel, 保存名)
PARAMS = [
    ("min_dark_count_rate",   "Dark Count Rate Distribution (Available)",   "Dark Count Rate [Hz]",   "available_dark_rate_histogram"),
    ("spe_gain_at_800v",      "SPE Gain Distribution (Available)",          "Gain @800V [10$^{6}$ e$^{-}$]", "available_gain_histogram"),
    ("min_energy_resolution", "Energy Resolution Distribution (Available)", "Energy Resolution",      "available_er_histogram"),
]


def plot_hist(values, title, xlabel, color, out_path, xticks=None):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(values, bins=15, color=color, alpha=0.85,
            edgecolor="white", linewidth=0.8)
    ax.axvline(values.mean(), color=COLOR_MEAN, linestyle="--", linewidth=2.0,
               label=f"mean = {values.mean():.3f}")
    ax.axvline(np.median(values), color=COLOR_MEDIAN, linestyle="-.", linewidth=2.0,
               label=f"median = {np.median(values):.3f}")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel("Counts", fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(axis="y", alpha=0.3)
    if xticks is not None:
        ax.set_xticks(xticks)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    df = pd.read_csv(DATA)
    print(f"可用候选 PMT 数: {len(df)}")

    # DCR
    plot_hist(df["min_dark_count_rate"],
              "Dark Count Rate Distribution (Available)",
              "Dark Count Rate [Hz]", COLOR_BAR,
              os.path.join(FIGS_DIR, "available_dark_rate_histogram.png"))

    # Gain
    plot_hist(df["spe_gain_at_800v"],
              "SPE Gain Distribution (Available)",
              "Gain @800V [10$^{6}$ e$^{-}$]", COLOR_BAR,
              os.path.join(FIGS_DIR, "available_gain_histogram.png"))

    # ER
    plot_hist(df["min_energy_resolution"],
              "Energy Resolution Distribution (Available)",
              "Energy Resolution", COLOR_BAR,
              os.path.join(FIGS_DIR, "available_er_histogram.png"))

    # APP — 只含有效 APP 数据
    app = df["app"].dropna()
    plot_hist(app,
              "After-Pulse Probability Distribution (Available)",
              "APP [%]", COLOR_BAR,
              os.path.join(FIGS_DIR, "available_app_histogram.png"))

    print("Done.")


if __name__ == "__main__":
    main()
