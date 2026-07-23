# PMTscope — PMT 性能参数诊断工具

用于快速查看、诊断光电倍增管（PMT）性能参数的网页交互工具。

## 安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml` 指定数据库路径：

```yaml
database:
  type: csv          # csv 或 sqlite
  path: data/pmt_data.csv
```

## 运行

```bash
source .venv/bin/activate
streamlit run app.py
```

## 生成示例数据

```bash
python generate_sample_data.py
```

## 功能

- **全局过滤器**：HV 范围、Run ID、PMT ID、Run Type/Tag、时间范围
- **参数直方图**：spe_gain、dark_count_rate、after_pulse_probability，支持 KDE 叠加
- **三维参数空间分布图**：可旋转缩放，点击查看数据点详情
- **趋势散点图**：参数 vs PMT ID，支持中心值线、离群点高亮
- **离群点预警**：3σ / IQR 两种检测规则
- **多 Run 对比**：直方图和趋势图支持同时对比多个 Run
- **快速查询面板**：按 pmt_id / run_id 查询，支持导出 CSV

## 项目结构

```
PMTscope/
├── app.py                    # 主入口
├── data_loader.py            # 数据加载与过滤
├── plots.py                  # Plotly 图表生成
├── utils.py                  # 统计计算与离群点检测
├── config.yaml               # 配置文件
├── requirements.txt          # 依赖列表
├── generate_sample_data.py   # 示例数据生成脚本
├── data/
│   └── pmt_data.csv          # 数据文件
└── docs/
    ├── inference.md          # 需求文档
    └── tasks.md              # 开发任务列表
```
