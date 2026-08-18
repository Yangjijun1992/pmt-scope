"""plot_selection_comparison.py — 全部 PMT vs 通过筛选 PMT 参数分布对比直方图（PMT 级别）

每个 PMT 在该参数上取一个代表值（与 select_candidates.py 筛选逻辑一致）：
  - DCR : 每只 PMT 的 min(dark_count_rate)
  - Gain: 每只 PMT 在 hv=800（NULL 视为 800）下的 max(spe_gain)
  - ER  : 每只 PMT 的 min(energy_resolution)
  - APP : 每只 PMT 的 max(after_pulse_probability) × 100（与 APP 排除检查一致）

然后对每个参数画叠加直方图：
  - 蓝色 = 全部 PMT（146 只中该参数有数据的）
  - 橙色 = 通过全部筛选条件的候选 PMT（candidates.csv，DCR<1200 规则下 82 只）

输出: figs/comparison_{dcr,gain,er,app}_histogram.png
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pmt-data-client", "data", "pmt_data.db")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS_DIR = os.path.join(ROOT, "figs")
CAND_PATH = os.path.join(ROOT, "docs", "candidates.csv")

COLOR_ALL = "#2B6FB3"       # blue: all PMTs
COLOR_SEL = "#E8652D"       # orange: selected candidates
COLOR_THRESHOLD = "#333333"

DCR_CUT = 1200.0
DCR_BINS = np.arange(0, 1301, 100)        # 0–1300 Hz, 100 Hz/bin
GAIN_BINS = np.arange(0, 15.01, 0.5)      # 0–15, 0.5/bin
ER_BINS = np.arange(0, 1.001, 0.05)       # 0–1, 0.05/bin
APP_BINS = np.arange(0, 30.01, 1.5)       # 0–30%, 1.5%/bin


def _load_candidates() -> pd.DataFrame:
    if os.path.exists(CAND_PATH):
        return pd.read_csv(CAND_PATH)
    raise FileNotFoundError(f"candidates.csv not found: {CAND_PATH}")


def per_pmt_values(db_path: str) -> pd.DataFrame:
    """按 PMT 聚合得到每只 PMT 的代表值（与筛选逻辑一致）。"""
    conn = sqlite3.connect(db_path)

    # DCR: min per pmt
    dcr = pd.read_sql("""
        SELECT pmt_id, MIN(dark_count_rate) AS dcr_min
        FROM measurements
        WHERE dark_count_rate IS NOT NULL
        GROUP BY pmt_id
    """, conn)

    # Gain: max at hv=800 (NULL -> 800) per pmt
    gain = pd.read_sql("""
        SELECT pmt_id, MAX(spe_gain) AS gain_800
        FROM measurements
        WHERE spe_gain IS NOT NULL AND (hv = 800 OR hv IS NULL)
        GROUP BY pmt_id
    """, conn)

    # ER: min per pmt
    er = pd.read_sql("""
        SELECT pmt_id, MIN(energy_resolution) AS er_min
        FROM measurements
        WHERE energy_resolution IS NOT NULL
        GROUP BY pmt_id
    """, conn)

    # APP: max per pmt (与 APP 排除检查一致), ×100 -> %
    app = pd.read_sql("""
        SELECT pmt_id, MAX(after_pulse_probability) * 100 AS app_max_pct
        FROM measurements
        WHERE after_pulse_probability IS NOT NULL
        GROUP BY pmt_id
    """, conn)

    conn.close()

    df = dcr.merge(gain, on="pmt_id", how="outer").merge(er, on="pmt_id", how="outer").merge(app, on="pmt_id", how="outer")
    return df


def plot_overlay(all_vals, sel_vals, bins, xlabel, title, out_path,
                 all_label, sel_label, xlim=None, vline=None):
    fig, ax = plt.subplots(figsize=(11, 6.5))

    ax.hist(all_vals, bins=bins, color=COLOR_ALL, alpha=0.45,
            edgecolor="white", linewidth=0.8, label=all_label)
    ax.hist(sel_vals, bins=bins, color=COLOR_SEL, alpha=0.65,
            edgecolor="white", linewidth=0.8, label=sel_label)

    ax.set_title(title, fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel("Counts", fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(axis="y", alpha=0.3)
    if xlim is not None:
        ax.set_xlim(xlim)
    if vline is not None:
        ax.axvline(vline[0], color=vline[1], linestyle="--", linewidth=2.5,
                   label=vline[2])
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    cands = _load_candidates()
    cand_ids = set(cands["pmt_id"])
    print(f"通过筛选候选 PMT 数: {len(cand_ids)}")

    allpmt = per_pmt_values(DB_PATH)
    print(f"全部 PMT 数(任一参数有数据): {len(allpmt)}")

    # ---- DCR ----
    a = allpmt["dcr_min"].dropna()
    s = cands["min_dark_count_rate"].dropna()
    print(f"DCR : all n={len(a)}, selected n={len(s)}")
    plot_overlay(a.values, s.values, bins=DCR_BINS, xlabel="Dark Count Rate [Hz]",
                 title="Dark Count Rate: All vs Selected (cut < 1200 Hz)",
                 out_path=os.path.join(FIGS_DIR, "comparison_dcr_histogram.png"),
                 all_label=f"All PMTs (n={len(a)})",
                 sel_label=f"Selected (n={len(s)})", xlim=(0, 1300),
                 vline=(DCR_CUT, COLOR_THRESHOLD, "Threshold: 1200 Hz"))

    # ---- Gain ----
    a = allpmt["gain_800"].dropna()
    s = cands["spe_gain_at_800v"].dropna()
    print(f"Gain : all n={len(a)}, selected n={len(s)}")
    plot_overlay(a.values, s.values, bins=GAIN_BINS, xlabel="Gain @800V [10$^{6}$ e$^{-}$]",
                 title="SPE Gain: All vs Selected (hv = 800 V)",
                 out_path=os.path.join(FIGS_DIR, "comparison_gain_histogram.png"),
                 all_label=f"All PMTs (n={len(a)})",
                 sel_label=f"Selected (n={len(s)})", xlim=(0, 15))

    # ---- ER ----
    a = allpmt["er_min"].dropna()
    s = cands["min_energy_resolution"].dropna()
    print(f"ER   : all n={len(a)}, selected n={len(s)}")
    plot_overlay(a.values, s.values, bins=ER_BINS, xlabel="Energy Resolution",
                 title="Energy Resolution: All vs Selected",
                 out_path=os.path.join(FIGS_DIR, "comparison_er_histogram.png"),
                 all_label=f"All PMTs (n={len(a)})",
                 sel_label=f"Selected (n={len(s)})", xlim=(0, 1))

    # ---- APP ----
    a = allpmt["app_max_pct"].dropna()
    s = cands["app"].dropna()
    print(f"APP  : all n={len(a)}, selected n={len(s)}")
    plot_overlay(a.values, s.values, bins=APP_BINS, xlabel="After-Pulse Probability [%]",
                 title="After-Pulse Probability: All vs Selected",
                 out_path=os.path.join(FIGS_DIR, "comparison_app_histogram.png"),
                 all_label=f"All PMTs (n={len(a)})",
                 sel_label=f"Selected (n={len(s)})", xlim=(0, 30))

    print("Done.")


if __name__ == "__main__":
    main()
