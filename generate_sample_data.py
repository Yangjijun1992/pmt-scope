"""生成示例 PMT 数据用于开发测试"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
n_pmts = 50
n_runs = 3
n_total = n_pmts * n_runs

pmt_ids = [f"PMT-{i:03d}" for i in range(n_pmts)]
run_ids = [f"R00{i+1}" for i in range(n_runs)]

data = []
base_time = datetime(2024, 1, 1, 10, 0, 0)

for i, pmt_id in enumerate(pmt_ids):
    for j, run_id in enumerate(run_ids):
        spe_gain = np.random.normal(1.5e6, 2e5)
        dark_count = np.random.exponential(500) + 50
        after_pulse = np.random.beta(2, 50) * 0.1
        if np.random.random() < 0.05:
            dark_count = np.random.uniform(5000, 10000)
            after_pulse = np.random.uniform(0.08, 0.15)

        data.append({
            "id": i * n_runs + j + 1,
            "pmt_id": pmt_id,
            "board_id": f"B{i // 10:02d}",
            "channel_id": i % 16,
            "measurement_time": base_time + timedelta(days=i * n_runs + j, hours=np.random.randint(0, 12)),
            "run_id": run_id,
            "run_type": np.random.choice(["calibration", "production", "test"]),
            "run_tag": np.random.choice(["v1.0", "v2.0", "v1.1"]),
            "hv": np.random.choice([1000, 1200, 1500, 1800, 2000]),
            "temperature": round(np.random.normal(25, 3), 1),
            "spe_gain": round(spe_gain, 0),
            "dark_count_rate": round(dark_count, 1),
            "after_pulse_probability": round(after_pulse, 6),
            "notes": "",
        })

df = pd.DataFrame(data)
df.loc[df.sample(frac=0.03).index, "notes"] = "校准异常"

df.to_csv("data/pmt_data.csv", index=False)
print(f"✅ 已生成 {len(df)} 条示例数据 → data/pmt_data.csv")
print(f"   PMT 数量: {n_pmts}, Run 数量: {n_runs}")
print(f"   字段: {list(df.columns)}")
