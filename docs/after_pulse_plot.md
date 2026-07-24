# plot_after_pulse.py — 后脉冲概率（After-Pulse Probability）独立绘图脚本

## 概述

从数据库读取所有 PMT 的 `after_pulse_probability` 数据，乘以 100 转换为百分比 `APP[%]`，绘制直方图并保存为 PNG 文件。

## 数据源

- 数据库：`/home/yjj/pmtdatabase/pmt-data-client/data/pmt_data.db`
- 表：`measurements`
- 列：`pmt_id`、`after_pulse_probability`、`run_id`
- 过滤：`after_pulse_probability IS NOT NULL`
- 聚合：按 `pmt_id` 分组取均值（`AVG(after_pulse_probability)`），每个 PMT 一个数据点
- 转换：所有数值 **×100**，单位由小数换算为百分比 `APP[%]`

### 数据概况

| 指标          | 值                                      |
| ------------- | --------------------------------------- |
| PMT 数量      | 46                                      |
| APP[%] 范围   | 1.39% ~ 19.12%                          |
| APP[%] 均值   | 4.24%                                   |
| APP[%] 中位数 | 3.63%                                   |
| APP[%] 标准差 | 2.84%                                   |
| 数据分布      | 高度集中在 ≤6%（41/46），长尾延伸至 19% |

---

## 图：APP 分布直方图

| 属性     | 值                                   |
| -------- | ------------------------------------ |
| 标题     | After-Pulse Probability Distribution |
| 横轴标签 | `APP [%]`                            |
| 横轴单位 | 百分比（%）                          |
| 纵轴标签 | 频次（PMT 数量）                     |
| Bin 数量 | 20                                   |
| 输出文件 | `figs/after_pulse_histogram.png`     |

### 实现要点

- 查询 `after_pulse_probability IS NOT NULL` 的所有行
- 按 `pmt_id` 分组取均值
- 均值 × 100 转换为 %
- 使用 `matplotlib` 绘制直方图，`bins=20`
- 添加均值线和/或中位数线（可选虚线标记）

---

## 依赖

- `matplotlib`
- `pandas`
- `sqlite3`
- `numpy`

## 产出文件

```bash
figs/after_pulse_histogram.png
```

## 运行

```bash
python plot_after_pulse.py
```

---

# 需求列表

| 编号 | 需求描述                                                                 |
| ---- | ------------------------------------------------------------------------ |
| R1   | 从 SQLite 数据库读取 `after_pulse_probability IS NOT NULL` 的所有记录    |
| R2   | 按 `pmt_id` 分组取 `after_pulse_probability` 均值（每个 PMT 一个数据点） |
| R3   | 所有数值 × 100，换算为百分比 `APP[%]`                                    |
| R4   | 绘制 APP[%] 分布直方图                                                   |
| R5   | 横轴标签为 `APP [%]`，纵轴标签为频次（PMT 数量）                         |
| R6   | Bin 数量设为 20                                                          |
| R7   | 保存为 PNG 文件到 `figs/after_pulse_histogram.png`                      |

---

# 任务清单

| 任务 | 状态                                                                          |
| ---- | ----------------------------------------------------------------------------- |
| T1   | 创建 `plots/` 输出目录（如不存在）                                            |
| T2   | 编写 SQL 查询：筛选 `after_pulse_probability IS NOT NULL`，按 `pmt_id` 取均值 |
| T3   | 将均值 × 100，转换为 `APP[%]`                                                 |
| T4   | 绘制直方图（`bins=20`），横轴 `APP [%]`，纵轴频次                             |
| T5   | 添加标题、轴标签、网格等样式                                                  |
| T6   | 保存为 `plots/after_pulse_histogram.png`（dpi≥150）                           |
| T7   | 编写 `plot_after_pulse.py` 主脚本                                             |
| T8   | 运行脚本，验证 PNG 产出正确                                                   |
