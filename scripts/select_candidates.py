"""筛选符合候选条件的 PMT。

条件：
  - dark_count_rate < 1000 Hz
  - spe_gain > 2
  - energy_resolution < 0.5
  - 在满足上述三条件的 pmt_id 中，排除其任意一条 after_pulse_probability > 0.1 的 PMT；
    若该 pmt_id 没有任何 after_pulse 测试记录，则保留该 pmt_id。

算法：
  1. SQL 按 (pmt_id, channel_id, run_id) 聚合取各指标 AVG 值
  2. 按 pmt_id 聚合：取 min(dark_count_rate)、max(spe_gain 仅限 hv=800)、min(energy_resolution)
  3. 筛选同时满足前三条件的 pmt_id 候选集
  4. 对候选集中的 pmt_id，逐一检查数据库中是否存在 after_pulse_probability > 0.1 的记录（原始表直查）
  5. 如果有违规记录则排除；如果无 after_pulse 记录则保留
"""

import os
import sqlite3
from typing import Tuple

import pandas as pd


DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "pmt-data-client", "data", "pmt_data.db"
)

DCR_MAX = 1000.0
GAIN_MIN = 2.0
ER_MAX = 0.5
APP_MAX = 0.1


def select_candidates(
    db_path: str = DB_PATH,
    dcr_max: float = DCR_MAX,
    gain_min: float = GAIN_MIN,
    er_max: float = ER_MAX,
    app_max: float = APP_MAX,
) -> Tuple[pd.DataFrame, dict]:
    """筛选符合全部条件的候选 PMT。

    Parameters
    ----------
    db_path : str
        SQLite 数据库路径。
    dcr_max : float
        dark_count_rate 上限。
    gain_min : float
        spe_gain 下限。
    er_max : float
        energy_resolution 上限。
    app_max : float
        after_pulse_probability 上限，
        对每个 pmt_id 检查其所有原始记录是否均不超过此值。

    Returns
    -------
    candidates : pd.DataFrame
        最终候选 PMT 列表，包含 min_dark_count_rate, spe_gain_at_800v,
        min_energy_resolution, n_records 列。
    summary : dict
        统计摘要。
    """
    # 步骤 1: 按 (pmt_id, channel_id, run_id) 聚合取平均值
    conn = sqlite3.connect(db_path)
    query = """
        SELECT pmt_id,
               channel_id,
               run_id,
               AVG(dark_count_rate)   AS dark_count_rate,
               AVG(spe_gain)          AS spe_gain,
               AVG(energy_resolution) AS energy_resolution,
               hv
        FROM measurements
        WHERE dark_count_rate IS NOT NULL
           OR spe_gain IS NOT NULL
           OR energy_resolution IS NOT NULL
        GROUP BY pmt_id, channel_id, run_id
    """
    df = pd.read_sql_query(query, conn)

    # 步骤 2: spe_gain 只取 hv=800 的数据，按 pmt_id 聚合取最大值
    gain_hv800 = (
        df[df["hv"] == 800]
        .groupby("pmt_id")["spe_gain"]
        .max()
        .reset_index()
        .rename(columns={"spe_gain": "spe_gain_at_800v"})
    )

    # 步骤 2–3: 按 pmt_id 聚合取最优值，筛选前三条件
    agg = df.groupby("pmt_id").agg(
        min_dark_count_rate=("dark_count_rate", "min"),
        min_energy_resolution=("energy_resolution", "min"),
        n_records=("pmt_id", "count"),
    ).reset_index()

    agg = agg.merge(gain_hv800, on="pmt_id", how="left")

    mask = (
        (agg["min_dark_count_rate"] < dcr_max)
        & (agg["spe_gain_at_800v"] > gain_min)
        & (agg["min_energy_resolution"] < er_max)
    )
    candidates = agg[mask].copy()

    # 步骤 4–5: after_pulse 检查
    candidate_ids = candidates["pmt_id"].tolist()
    failures = set()

    for pid in candidate_ids:
        cur = conn.execute(
            "SELECT 1 FROM measurements"
            " WHERE pmt_id = ?"
            "   AND after_pulse_probability IS NOT NULL"
            "   AND after_pulse_probability > ?"
            " LIMIT 1",
            (pid, app_max),
        )
        if cur.fetchone() is not None:
            failures.add(pid)

    # 统计有 after_pulse 记录的数量
    total = len(candidate_ids)
    with_app = set()
    for pid in candidate_ids:
        cur = conn.execute(
            "SELECT 1 FROM measurements"
            " WHERE pmt_id = ? AND after_pulse_probability IS NOT NULL LIMIT 1",
            (pid,),
        )
        if cur.fetchone() is not None:
            with_app.add(pid)

    conn.close()

    # 过滤
    final_ids = set(candidate_ids) - failures
    candidates = candidates[candidates["pmt_id"].isin(final_ids)].copy()
    candidates.sort_values("pmt_id", inplace=True)
    candidates.reset_index(drop=True, inplace=True)

    summary = {
        "total_pmts": df["pmt_id"].nunique(),
        "candidates_after_step3": total,
        "with_after_pulse_data": len(with_app),
        "without_after_pulse_data": total - len(with_app),
        "rejected_by_after_pulse": len(failures),
        "rejected_ids": sorted(failures),
        "final_count": len(candidates),
        "with_app_ids": with_app,
    }

    return candidates, summary


def main():
    candidates, summary = select_candidates()

    print(f"前三条件:")
    print(f"  dark_count_rate        < {DCR_MAX}")
    print(f"  spe_gain               > {GAIN_MIN}")
    print(f"  energy_resolution      < {ER_MAX}")
    print(f"\n  通过前三条件的 pmt_id: {summary['candidates_after_step3']}")
    print(f"  其中有 after_pulse 测试记录的: {summary['with_after_pulse_data']}")
    print(f"  其中无 after_pulse 测试记录的: {summary['without_after_pulse_data']}")
    print(f"  因 after_pulse > {APP_MAX} 被排除的: {summary['rejected_by_after_pulse']}")
    if summary["rejected_ids"]:
        print(f"  被排除的 pmt_id: {', '.join(summary['rejected_ids'])}")

    print(f"\n总 PMT 数: {summary['total_pmts']}")
    print(f"最终候选 PMT 数: {summary['final_count']}")
    print(f"\n最终候选 PMT 列表:")
    print("-" * 62)
    print(
        f"{'pmt_id':<20s}"
        f"{'min_dcr':>10s}"
        f"{'gain_800v':>10s}"
        f"{'min_er':>10s}"
        f"{'records':>8s}"
    )
    print("-" * 62)

    for _, row in candidates.iterrows():
        gain = row['spe_gain_at_800v']
        gain_str = f"{gain:.2f}" if pd.notna(gain) else "  -"
        print(
            f"{row['pmt_id']:<20s}"
            f"{row['min_dark_count_rate']:>10.2f}"
            f"{gain_str:>10s}"
            f"{row['min_energy_resolution']:>10.4f}"
            f"{row['n_records']:>8d}"
        )

    print("-" * 62)

    if len(candidates) > 0:
        candidates.to_csv("candidates.csv", index=False, float_format="%.4f")
        print("\n结果已保存到 candidates.csv")

    # 单独保存无 after_pulse 记录的候选
    without_app = candidates[~candidates["pmt_id"].isin(summary["with_app_ids"])].copy()
    if len(without_app) > 0:
        without_app.to_csv("candidates_without_after_pulse.csv", index=False, float_format="%.4f")
        print(f"无 after_pulse 测试记录的 {len(without_app)} 个候选已保存到 candidates_without_after_pulse.csv")


if __name__ == "__main__":
    main()
