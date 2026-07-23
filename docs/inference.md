# PMTscope - 需求文档 v2.1

## 1. 项目概述

**PMTscope** 是一个独立的网页交互工具，用于快速查看、诊断光电倍增管（PMT）的性能参数。它通过三维可视化、直方图与趋势分析，帮助科研人员高效识别性能异常与分布规律。

## 2. 数据源与字段

工具读取一个已有的 PMT 数据库（SQLite / CSV），至少包含以下字段：

| 字段名                    | 说明           |
| ------------------------- | -------------- |
| `id`                      | 唯一记录标识   |
| `pmt_id`                  | PMT 编号或标签 |
| `board_id`                | 板卡编号       |
| `channel_id`              | 通道号         |
| `measurement_time`        | 测量时间戳     |
| `run_id`                  | 运行批次 ID    |
| `run_type`                | 运行类型       |
| `run_tag`                 | 运行标签       |
| `hv`                      | 高压值（V）    |
| `temperature`             | 温度（°C）     |
| `spe_gain`                | 单光子增益     |
| `dark_count_rate`         | 暗计数率（Hz） |
| `after_pulse_probability` | 后脉冲概率     |
| `notes`                   | 备注信息       |

## 3. 功能需求

### F1. 全局过滤器

在侧边栏提供筛选控件，支持的过滤维度包括：

- `hv` 范围（滑块）
- `run_id`（多选下拉框）
- `pmt_id`（多选下拉框，支持搜索）
- `run_type` / `run_tag`（可选）
- 时间范围（基于 `measurement_time`）

**行为：** 任一过滤条件改变时，页面内所有图表同步刷新，仅显示满足条件的记录。

### F2. 参数直方图

分别绘制 `spe_gain`、`dark_count_rate`、`after_pulse_probability` 的直方图。

- 支持动态调整 bin 数量（滑块控制）。
- 允许叠加核密度估计（KDE）曲线。
- 支持 zoom in / pan（通过 Plotly 内置交互）。

### F3. 三维参数空间分布图

以 `spe_gain`、`dark_count_rate`、`after_pulse_probability` 为 X、Y、Z 轴绘制三维散点图。

- 自动跳过三个参数中任一缺失的记录。
- 点颜色可按 `pmt_id` 或 `run_id` 映射（可选）。
- 支持旋转、缩放。
- **点击交互：** 当用户点击 3D 图中的某个点时，在页面指定区域（如右侧信息面板）显示该数据点的全部字段信息（包括 `id`、`pmt_id`、`hv`、`measurement_time`、`notes` 等）。

### F4. 参数 vs. PMT ID 趋势散点图

绘制以下三张散点图：

- `spe_gain` vs `pmt_id`
- `dark_count_rate` vs `pmt_id`
- `after_pulse_probability` vs `pmt_id`

每张图中：

- X 轴为 `pmt_id`（建议按数值或字典序排列）。
- 添加一条水平虚线，表示当前所选数据的 **中心值**（可选用中位数或均值，由用户在 UI 中选择）。
- **悬停信息：** 鼠标悬停或点击数据点时，显示该点的完整参数（`run_id`, `hv`, `temperature`, `notes` 等）。
- 支持 zoom in 和矩形框选。

### F5. 离群点预警（Outlier Highlighting）

在直方图和趋势散点图中，自动标识离群点：

- 使用 3σ（标准偏差）或 IQR（四分位距）规则（可配置）。
- 离群点用醒目的颜色（如红色）标注。
- 在趋势图上，离群点旁边的 `pmt_id` 标签高亮显示。

### F6. 多 Run 对比（Multi-Run Comparison）

允许用户同时选择 **两个或更多** `run_id`（通过过滤器多选或专用对比控件）：

- 直方图：以半透明重叠或分组柱状图显示不同 run 的分布。
- 3D 图：不同 run 的点使用不同颜色/符号。
- 趋势图：仍以 `pmt_id` 为 X 轴，每个 run 的数据点叠加在同一图中，便于比较同 PMT 在不同实验条件下的变化。

### F7. 快速查询面板（新增）

在侧边栏或独立区域提供一个查询框，用户可以输入一个 `pmt_id` 或 `run_id`，点击“查询”按钮后，以表格形式展示该 PMT 或该 Run 的**所有记录的全部字段**。

- 若输入 `pmt_id`，显示该 PMT 所有历史测量记录。
- 若输入 `run_id`，显示该 Run 下所有 PMT 的记录。
- 支持同时输入两个值（用逗号分隔），如 `pmt_id=001, run_id=R123`，则进行组合查询。
- 查询结果表格支持排序、搜索、导出 CSV。

## 4. 交互与性能要求

- **响应式联动：** 所有图表基于统一的数据视图，通过过滤器联动。
- **Zoom & 平移：** 全部 Plotly 图表默认启用内置工具栏（zoom, pan, reset, download as PNG）。
- **数据点详情阅读：** 3D 图点击 → 面板展示详情；2D 散点图悬停 → tooltip 显示自定义字段。
- **数据量：** 总 PMT 数量 < 200，无需特殊性能优化，保持直接全量加载。

## 5. 技术栈建议

- **语言：** Python 3.10+
- **框架：** Streamlit（首选，快速开发） 或 Dash
- **数据处理：** Pandas，NumPy
- **可视化：** Plotly Express & Graph Objects
- **配置管理：** 通过 `.env` 或 `config.yaml` 指定数据库路径

## 6. 项目结构（推荐）

PMTscope/
├── app.py # 主入口，Streamlit 页面
├── data_loader.py # 数据读取、清洗、过滤逻辑
├── plots.py # 所有 Plotly 图表生成函数
├── utils.py # 统计计算（中心值、离群点检测）
├── config.yaml # 数据库路径等配置
├── requirements.txt
└── README.md

## 7. 验收标准

1. 根据数据库路径启动应用，页面能正确显示所有图表。
2. 选择不同过滤器，图表同步更新且无残留数据。
3. 3D 图中点击任意点，右侧信息面板准确显示该点全部字段。
4. 趋势图中悬停显示 `pmt_id`, `run_id`, `hv` 等关键字段。
5. 离群点在直方图和趋势图上被高亮为红色。
6. 选择两个不同 `run_id`，图表能正确进行对比显示。
7. 支持导出图表为静态图片（Plotly 内置）。
8. 在快速查询框中输入 `pmt_id` 或 `run_id`，能正确列出所有相关记录的全部信息。
