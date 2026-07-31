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

## 推荐部署：Streamlit Community Cloud（公网访问）

将应用部署到 Streamlit Cloud，校外用户无需 VPN 即可通过浏览器访问。数据托管在 GitHub **私有仓库**，不会公开泄露。

### 第一步：准备 GitHub 私有仓库

代码和数据已推送到私有仓库。确保仓库为 **Private**：

```bash
# 确认远程地址
git remote -v
```

### 第二步：部署到 Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 用 GitHub 账号登录
3. 点击 **New app** → 选择仓库 `Yangjijun1992/pmt-scope`
4. Main file path: `web/app.py`
5. 点击 **Advanced settings** → 选择 Python 版本（3.10+）
6. 点击 **Deploy**

### 第三步：配置认证凭据（Secrets）

在 Streamlit Cloud 的 App Settings → **Secrets** 中添加：

```toml
PMTSCOPE_USERNAME = "your_username"
PMTSCOPE_PASSWORD = "your_password"
```

凭据通过 Streamlit Secrets 注入，不会出现在仓库代码或日志中。

### 第四步：同步数据

在内网服务器上运行同步脚本，将 SQLite 数据导出为 CSV 并推送到 GitHub：

```bash
./web/sync_and_deploy.sh
```

脚本执行流程：
1. 从 `/mnt/data/TPC/database/pmt_data.db` 导出 `measurements` 表 → `data/pmt_data.csv`
2. `git commit` CSV 文件
3. `git push` 到 GitHub

Streamlit Cloud 检测到推送后会自动重新部署，新数据即可在网页端查看。

建议配合 cron 定时执行：

```bash
# 每天凌晨 2 点自动同步
0 2 * * * cd /home/yjj/pmtdatabase/pmt-scope && ./web/sync_and_deploy.sh >> sync.log 2>&1
```

### 访问

部署完成后，Streamlit Cloud 会分配一个公网 URL：`https://pmt-scope-xxxx.streamlit.app`

校外用户打开该 URL，输入用户名密码即可访问。

---

## 本地/内网运行

如需在内网服务器上运行：

```bash
# 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置凭据
cp web/.env.example .env
# 编辑 .env 填入实际用户名和密码

# 编辑 web/config.yaml 选择数据源
# database.type: csv  → 使用 data/pmt_data.csv
# database.type: sqlite → 使用 /mnt/data/TPC/database/pmt_data.db

# 启动
streamlit run web/app.py
```

或使用启动脚本常驻后台：

```bash
./web/start.sh start    # 启动
./web/start.sh stop     # 停止
./web/start.sh status   # 查看状态
```

## 项目结构

```
pmt-scope/
├── web/                          # Streamlit 远程网页端
│   ├── app.py                    # 主入口（含用户认证）
│   ├── plots.py                  # Plotly 交互式图表生成
│   ├── config.yaml               # 数据库与可视化配置
│   ├── requirements.txt          # Python 依赖
│   ├── start.sh                  # 本地/内网 启动/停止/状态脚本
│   ├── sync_and_deploy.sh        # 数据同步 → GitHub → Streamlit Cloud 自动部署
│   ├── pmtscope.service          # systemd 服务文件
│   └── .env.example              # 凭据模板（本地用）
│
├── scripts/                      # 本地离线画图与数据处理
│   ├── plot_gain.py              # SPE Gain 直方图 + 散点图 (matplotlib → PNG)
│   ├── plot_dark_rate.py         # Dark Count Rate 直方图 + 散点图 (matplotlib → PNG)
│   ├── plot_after_pulse.py       # After-Pulse Probability 直方图 (matplotlib → PNG)
│   ├── plot_energy_resolution.py # Energy Resolution 直方图 + 散点图 (matplotlib → PNG)
│   ├── select_candidates.py      # 候选 PMT 筛选（按 DCR/Gain/ER/APP 条件）
│   └── generate_sample_data.py   # 示例数据生成
│
├── data_loader.py                # 共用：数据加载与过滤（支持 CSV / SQLite）
├── utils.py                      # 共用：统计计算与离群点检测
│
├── data/
│   └── pmt_data.csv              # 数据文件（CSV 模式，由 sync_and_deploy.sh 生成）
├── docs/
│   ├── inference.md              # 需求文档
│   ├── tasks.md                  # 开发任务列表
│   ├── overlap_pmt_ids.csv       # 科大+西湖重复计数 PMT 列表
│   └── ...                       # 其他绘图规格和统计文档
├── figs/                         # scripts/ 输出的 PNG 图片
├── .streamlit/
│   └── secrets.toml.example      # Streamlit Secrets 模板
├── .gitignore
└── README.md
```
