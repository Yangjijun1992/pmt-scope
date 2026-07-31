"""plot_after_pulse.py — 后脉冲概率（After-Pulse Probability）直方图

所有数值 ×100 换算为 APP[%]，绘制直方图。

数据源: ../pmt-data-client/data/pmt_data.db
输出: figs/after_pulse_histogram.png
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
BINS = 20

COLOR_BAR = "#4C78A8"
COLOR_MEDIAN = "#D62728"
COLOR_MEAN = "#9467BD"


def load_data(db_path: str) -> np.ndarray:
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               AVG(after_pulse_probability) AS avg_app
        FROM measurements
        WHERE after_pulse_probability IS NOT NULL
        GROUP BY pmt_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    app_percent = (df["avg_app"] * 100).values
    return app_percent


def plot_histogram(app_values: np.ndarray, out_path: str):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(app_values, bins=BINS, color=COLOR_BAR, alpha=0.85, edgecolor="white", linewidth=0.8)

    ax.axvline(5.0, color=COLOR_MEDIAN, linestyle="--", linewidth=3.0,
               label="Threshold: 5%")

    ax.set_xlabel("APP [%]", fontsize=14, x=0.94, ha="right")
    ax.set_ylabel("Counts", fontsize=14)
    ax.set_title("After-Pulse Probability Distribution", fontsize=16, fontweight="bold")
    ax.tick_params(axis="both", labelsize=12)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved: {out_path}")


def main():
    app_values = load_data(DB_PATH)
    print(f"Loaded {len(app_values)} PMTs with after-pulse probability")
    print(f"  APP[%] range: {app_values.min():.2f}% – {app_values.max():.2f}%")
    print(f"  APP[%] mean:  {app_values.mean():.2f}%")
    print(f"  APP[%] median:{np.median(app_values):.2f}%")
    print(f"  APP[%] std:   {app_values.std():.2f}%")

    out_path = os.path.join(FIGS_DIR, "after_pulse_histogram.png")
    plot_histogram(app_values, out_path)

    print("Done.")


if __name__ == "__main__":
    main()
