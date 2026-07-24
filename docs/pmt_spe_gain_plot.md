更新后的任务文档内容：

# plot_gain.py — SPE Gain 独立绘图脚本

## 概述

从数据库读取 `spe_gain` 数据，生成两张图并保存为 PNG 文件。

## 数据源

- 数据库：`/home/yjj/pmtdatabase/pmt-data-client/data/pmt_data.db`
- 表：`measurements`
- 列：`pmt_id`、`run_id`、`spe_gain`
- 过滤：`spe_gain IS NOT NULL`

## 图 1：直方图

| 属性     | 值                         |
| -------- | -------------------------- |
| 标题     | SPE Gain Distribution      |
| 横轴标签 | `Gain [1.E6 e⁻]`           |
| 横轴范围 | `[-5, 30]`                 |
| Bin 数量 | 35                         |
| 纵轴标签 | 频次                       |
| 输出文件 | `figs/gain_histogram.png` |

## 图 2：散点图

| 属性       | 值                                       |
| ---------- | ---------------------------------------- |
| 标题       | SPE Gain vs PMT ID                       |
| Y 轴       | spe_gain                                 |
| Y 轴标签   | `Gain [1.E6 e⁻]`                         |
| X 轴       | pmt_id（字符串排序）                     |
| X 轴标签   | PMT ID                                   |
| 均值线     | 水平虚线，标注 `Median: xxx`             |
| 离群点标注 | 3σ 规则，标记异常的 `pmt_id` 和 `run_id` |
| 输出文件   | `figs/gain_scatter.png`                 |

## 依赖

- `matplotlib`
- `pandas`
- `sqlite3`
- `numpy`

## 运行

```bash
python plot_gain.py
```
