# plot_dark_rate.py — 暗计数率（Dark Count Rate）独立绘图脚本

## 概述

从数据库读取所有 PMT 的 `dark_count_rate` 数据，生成两张图并保存为 PNG 文件。

## 数据源

- 数据库：`/home/pmtdatabase/pmt-data-client/data/pmt_data.db`
- 表：`measurements`
- 列：`pmt_id`、`dark_count_rate`、`run_id`、`run_type`
- 聚合：按 `pmt_id` 分组取均值（`AVG(dark_count_rate)`），每个 PMT 一个数据点

<br>
- - -

## 图 1：暗计数率分布直方图

| 属性     | 值                                                                   |
| -------- | -------------------------------------------------------------------- |
| 标题     | Dark Count Rate Distribution                                         |
| 横轴标签 | `Dark Count Rate [Hz]`                                               |
| 横轴范围 | `[50, 5000]`                                                         |
| Bin 数量 | 自动（根据数据密度）                                                 |
| 纵轴标签 | 频次（PMT 数量）                                                     |
| 颜色规则 | <1000 Hz → **蓝色**；1000\~2000 Hz → **橙红色**；>2000 Hz → **红色** |
| 输出文件 | `figs/dark_rate_histogram.png`                                      |

### 着色实现要点

- 将数据分成 3 组：`<1000`、`1000-2000`、`>2000`
- 每组对应一个 `go.Histogram` trace，分别设置颜色
- 超出 2000 Hz 的分量使用醒目红色，与 1000 以下形成鲜明对比

---

## 图 2：暗计数率 vs PMT ID 散点图

| 属性       | 值                                                                                            |
| ---------- | --------------------------------------------------------------------------------------------- |
| 标题       | Dark Count Rate vs PMT ID                                                                     |
| Y 轴       | 暗计数率均值（`dark_count_rate`）                                                             |
| Y 轴标签   | `Dark Count Rate [Hz]`                                                                        |
| X 轴       | `pmt_id`（字符串排序）                                                                        |
| X 轴标签   | PMT ID                                                                                        |
| 中心线     | 水平虚线，标注 `Median: xxx Hz`                                                               |
| 数据点形状 | `<1000 Hz` → **蓝色实心圆 ●**；`1000~2000 Hz` → **橙红色三角 ▲**；`>2000 Hz` → **红色叉号 ×** |
| 离群点标注 | `dark_count_rate > 2000 Hz` 的 PMT，在其数据点旁边显示 `pmt_id` 文本标签                      |
| 输出文件   | `figs/dark_rate_scatter.png`                                                                 |

### 散点图实现要点

- X 轴按字符串排序所有 `pmt_id`
- Y 轴为每个 PMT 的暗计数率均值
- 虚线标注中位数（median）值
- 三组数据分别用不同的 `go.Scatter` trace，设置 `mode='markers+text'`（>2000 组需要文本标注）
- \>2000 Hz 的文本标签为 `pmt_id`，位置在数据点上方或右侧

---

## 依赖

- `matplotlib`
- `pandas`
- `sqlite3`
- `numpy`

## 产出文件

```bash
figs/dark_rate_histogram.png
figs/dark_rate_scatter.png
```

## 运行

```bash
python plot_dark_rate.py
```

---

# 需求列表

| 编号 | 需求描述                                                                           |
| ---- | ---------------------------------------------------------------------------------- |
| R1   | 从 SQLite 数据库读取 `dark_count_rate IS NOT NULL` 的所有记录                      |
| R2   | 按 `pmt_id` 分组取暗计数率均值（每个 PMT 一个数据点）                              |
| R3   | 过滤暗计数率范围：50 ≤ dark_count_rate ≤ 5000 Hz                                   |
| R4   | 图 1：绘制暗计数率分布直方图                                                       |
| R5   | 图 1：横轴范围 [50, 5000] Hz                                                       |
| R6   | 图 1：<1000 Hz 的 bin 着蓝色，1000\~2000 Hz 着橙红色，>2000 Hz 着红色              |
| R7   | 图 2：绘制 dark_count_rate vs pmt_id 散点图                                        |
| R8   | 图 2：<1000 Hz 用蓝色实心圆 ●，1000\~2000 Hz 用橙红色三角 ▲，>2000 Hz 用红色叉号 × |
| R9   | 图 2：添加水平虚线标注中位数（median）                                             |
| R10  | 图 2：>2000 Hz 的数据点旁边标注 `pmt_id` 文本                                      |
| R11  | 两图均保存为 PNG 文件到 `figs/` 目录                                               |

---

# 任务清单

| 任务 | 状态                                                                       |
| ---- | -------------------------------------------------------------------------- |
| T1   | 创建 `plots/` 输出目录（如不存在）                                         |
| T2   | 编写 SQL 查询：筛选 `dark_count_rate IS NOT NULL` 并按 `pmt_id` 分组取均值 |
| T3   | 过滤 `[50, 5000]` Hz 范围内的数据                                          |
| T4   | 将数据按暗计数率拆分为 3 组：`<1000`、`1000-2000`、`>2000`                 |
| T5   | 绘制直方图：3 个颜色的 `hist` trace 叠加                                   |
| T6   | 设置直方图轴标签、标题、横轴范围、图例                                     |
| T7   | 绘制散点图：3 个 scatter trace（蓝色实心圆、橙红三角、红色叉号）           |
| T8   | 在散点图上绘制中位数水平虚线                                               |
| T9   | 为 >2000 Hz 数据点添加 `pmt_id` 文本标签                                   |
| T10  | 设置散点图轴标签、标题、图例                                               |
| T11  | 保存直方图为 `plots/dark_rate_histogram.png`                               |
| T12  | 保存散点图为 `plots/dark_rate_scatter.png`                                 |
| T13  | 编写 `plot_dark_rate.py` 主脚本                                            |
| T14  | 运行脚本，验证 PNG 文件产出正确                                            |
