# PMTscope — PMT 性能参数诊断工具

用于快速查看、诊断光电倍增管（PMT）性能参数的网页交互工具。

## 功能

- **用户认证**：需用户名密码登录，支持多用户访问
- **全局过滤器**：HV 范围、Run ID、PMT ID、Run Type/Tag、时间范围
- **参数直方图**：spe_gain、dark_count_rate、after_pulse_probability，支持 KDE 叠加
- **三维参数空间分布图**：可旋转缩放，点击查看数据点详情
- **趋势散点图**：参数 vs PMT ID，支持中心值线、离群点高亮
- **离群点预警**：3σ / IQR 两种检测规则
- **多 Run 对比**：直方图和趋势图支持同时对比多个 Run
- **快速查询面板**：按 pmt_id / run_id 查询，支持导出 CSV

## 安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 生成示例数据（可选，用于本地测试）
python generate_sample_data.py
```

## 配置凭据（重要）

1. 复制凭据模板为 `.env` 文件：

```bash
cp .env.example .env
```

2. 编辑 `.env` 填入实际的用户名和密码：

```
PMTSCOPE_USERNAME=your_username
PMTSCOPE_PASSWORD=your_password
```

> `.env` 已在 `.gitignore` 中排除，不会被提交到远程仓库。

3. 编辑 `config.yaml` 指定数据库路径：

```yaml
database:
  type: csv          # csv 或 sqlite
  path: data/pmt_data.csv
```

## 本地运行

```bash
source .venv/bin/activate
streamlit run app.py
```

默认监听 `http://localhost:8501`，浏览器打开后输入 `.env` 中配置的用户名和密码即可登录。

## 公网部署

推荐使用 **Streamlit Community Cloud** 或自行部署到云服务器。

### Streamlit Community Cloud

1. 将代码推送到 GitHub 仓库
2. 在 [share.streamlit.io](https://share.streamlit.io) 连接仓库并创建 App
3. 在 App Settings → Secrets 中添加：

```
PMTSCOPE_USERNAME = "your_username"
PMTSCOPE_PASSWORD = "your_password"
```

### 自行部署（Linux 服务器）

```bash
# 安装依赖
source .venv/bin/activate
pip install -r requirements.txt

# 配置 .env 凭据
cp .env.example .env
vim .env  # 填入实际凭据

# 后台运行（监听所有网络接口）
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 &
```

使用 Nginx 反向代理可配置 HTTPS 和自定义域名。

## 项目结构

```
PMTscope/
├── app.py                    # 主入口（含用户认证）
├── data_loader.py            # 数据加载与过滤
├── plots.py                  # Plotly 图表生成
├── utils.py                  # 统计计算与离群点检测
├── config.yaml               # 数据库与可视化配置
├── .env.example              # 凭据模板
├── .gitignore                # Git 忽略规则
├── requirements.txt          # 依赖列表
├── generate_sample_data.py   # 示例数据生成脚本
├── data/
│   └── pmt_data.csv          # 数据文件
└── docs/
    ├── inference.md          # 需求文档
    └── tasks.md              # 开发任务列表
```
