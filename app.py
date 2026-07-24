"""PMTscope — PMT 性能参数诊断工具主入口"""

import os
import streamlit as st
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from data_loader import load_config, load_data, filter_data, query_records, parse_query_string
from plots import (
    plot_histogram, plot_histogram_compare,
    plot_3d_scatter,
    plot_trend_scatter, plot_trend_compare,
)
from utils import detect_outliers_df

load_dotenv()

st.set_page_config(
    page_title="PMTscope",
    page_icon="🔬",
    layout="wide",
)

# ── 用户认证 ────────────────────────────────────────────────────

def _get_credentials():
    """从 st.secrets (Streamlit Cloud) 或 .env (本地) 读取凭据。"""
    try:
        username = st.secrets["PMTSCOPE_USERNAME"]
        password = st.secrets["PMTSCOPE_PASSWORD"]
        return username, password
    except (KeyError, FileNotFoundError, AttributeError):
        return os.getenv("PMTSCOPE_USERNAME", ""), os.getenv("PMTSCOPE_PASSWORD", "")

VALID_USERNAME, VALID_PASSWORD = _get_credentials()


def check_password():
    """登录验证，返回 True 表示通过。"""

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["login_error"] = False

    if st.session_state["authenticated"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔬 PMTscope")
        st.markdown("PMT 性能参数诊断工具 · 请登录后使用")

        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", width="stretch")

            if submitted:
                if username == VALID_USERNAME and password == VALID_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.session_state["login_error"] = False
                    st.rerun()
                else:
                    st.session_state["login_error"] = True

        if st.session_state.get("login_error"):
            st.error("用户名或密码错误，请重试。")

    return False


if not check_password():
    st.stop()


def logout():
    st.session_state["authenticated"] = False
    st.session_state["login_error"] = False


# ── 加载配置与数据 ──────────────────────────────────────────────

@st.cache_data
def get_config():
    return load_config("config.yaml")


@st.cache_data
def get_raw_data(_config: dict):
    return load_data(_config)


config = get_config()
raw_df = get_raw_data(config)

cfg_viz = config.get("visualization", {})
cfg_outlier = config.get("outlier", {})
cfg_center = config.get("center", {})

# ── 侧边栏 ──────────────────────────────────────────────────────

with st.sidebar:
    st.title("🔬 PMTscope")
    st.markdown("PMT 性能参数诊断工具")

    if st.button("🚪 退出登录", width="stretch"):
        logout()
        st.rerun()

    st.header("📋 全局过滤器")

    hv_min = 500.0
    hv_max = 2000.0
    actual_hv_min = float(raw_df["hv"].min()) if "hv" in raw_df.columns and raw_df["hv"].notna().any() else hv_min
    actual_hv_max = float(raw_df["hv"].max()) if "hv" in raw_df.columns and raw_df["hv"].notna().any() else hv_max
    hv_range = st.slider(
        "高压值 (HV) 范围",
        min_value=float(actual_hv_min), max_value=float(actual_hv_max),
        value=(float(actual_hv_min), float(actual_hv_max)),
        step=1.0,
    )

    all_run_ids = sorted(raw_df["run_id"].dropna().unique().tolist()) if "run_id" in raw_df.columns else []
    selected_run_ids = st.multiselect("Run ID", options=all_run_ids, default=[])

    all_pmt_ids = sorted(raw_df["pmt_id"].dropna().unique().tolist()) if "pmt_id" in raw_df.columns else []
    selected_pmt_ids = st.multiselect("PMT ID（支持搜索）", options=all_pmt_ids, default=[])

    if "run_type" in raw_df.columns:
        all_run_types = sorted(raw_df["run_type"].dropna().unique().tolist())
        selected_run_types = st.multiselect("Run Type", options=all_run_types, default=[])
    else:
        selected_run_types = []

    if "run_tag" in raw_df.columns:
        all_run_tags = sorted(raw_df["run_tag"].dropna().unique().tolist())
        selected_run_tags = st.multiselect("Run Tag", options=all_run_tags, default=[])
    else:
        selected_run_tags = []

    if "measurement_time" in raw_df.columns and pd.api.types.is_datetime64_any_dtype(raw_df["measurement_time"]):
        time_min = raw_df["measurement_time"].min().to_pydatetime()
        time_max = raw_df["measurement_time"].max().to_pydatetime()
        time_range = st.date_input(
            "时间范围",
            value=(time_min.date(), time_max.date()),
        )
    else:
        time_range = None

    st.divider()

    st.header("⚙️ 可视化设置")

    default_bin = cfg_viz.get("default_bin_count", 30)
    bin_count = st.slider("直方图 Bin 数量", min_value=5, max_value=100, value=default_bin)

    show_kde = st.checkbox("叠加 KDE 曲线", value=cfg_viz.get("show_kde", False))

    center_method = st.radio("中心值方法", options=["median", "mean"], index=0 if cfg_center.get("method", "median") == "median" else 1)

    st.divider()

    st.header("🚨 离群点设置")

    enable_outlier = st.checkbox("启用离群点高亮", value=True)
    outlier_method = st.radio(
        "检测规则",
        options=["iqr", "sigma"],
        index=0 if cfg_outlier.get("method", "iqr") == "iqr" else 1,
        format_func=lambda x: "IQR (四分位距)" if x == "iqr" else "3σ (标准偏差)",
    )
    outlier_mult = cfg_outlier.get("iqr_multiplier", 1.5) if outlier_method == "iqr" else cfg_outlier.get("sigma_multiplier", 3.0)
    outlier_mult = st.number_input("倍数", value=outlier_mult, min_value=0.5, max_value=10.0, step=0.5)

    st.divider()

    st.header("🔍 快速查询")

    query_input = st.text_input("输入 pmt_id 或 run_id（逗号分隔）", placeholder="例如: pmt_id=001, run_id=R123")
    query_btn = st.button("查询", width="stretch")

# ── 数据过滤 ────────────────────────────────────────────────────

filtered_df = filter_data(
    raw_df,
    hv_range=hv_range,
    run_ids=selected_run_ids if selected_run_ids else None,
    pmt_ids=selected_pmt_ids if selected_pmt_ids else None,
    run_types=selected_run_types if selected_run_types else None,
    run_tags=selected_run_tags if selected_run_tags else None,
    time_range=(
        (pd.Timestamp(time_range[0]), pd.Timestamp(time_range[1]))
        if time_range is not None and len(time_range) == 2
        else None
    ),
)

# ── 离群点检测 ──────────────────────────────────────────────────

outlier_columns = ["spe_gain", "dark_count_rate", "after_pulse_probability"]
if enable_outlier:
    filtered_df = detect_outliers_df(
        filtered_df, outlier_columns,
        method=outlier_method, multiplier=outlier_mult,
    )
else:
    for col in outlier_columns:
        filtered_df[f"{col}_outlier"] = False

# ── 主页面 ──────────────────────────────────────────────────────

st.title("PMTscope — PMT 性能参数诊断")
st.caption(f"当前显示 {len(filtered_df)} / {len(raw_df)} 条记录")

# ── 快速查询面板 ────────────────────────────────────────────────

if query_btn and query_input.strip():
    parsed = parse_query_string(query_input.strip())
    if parsed["pmt_id"] or parsed["run_id"]:
        query_df = query_records(raw_df, pmt_id=parsed["pmt_id"], run_id=parsed["run_id"])
        st.subheader("🔍 查询结果")
        st.caption(f"找到 {len(query_df)} 条记录")
        st.dataframe(
            query_df,
            width="stretch",
            hide_index=True,
            column_config={col: st.column_config.TextColumn(col) for col in query_df.columns},
        )

        csv_data = query_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 导出 CSV",
            data=csv_data,
            file_name=f"pmt_query_{parsed.get('pmt_id', parsed.get('run_id', 'result'))}.csv",
            mime="text/csv",
        )
    else:
        st.warning("无法解析查询字符串，请使用格式: pmt_id=xxx 或 run_id=xxx")

# ── 参数直方图 ──────────────────────────────────────────────────

HIST_TITLES = {
    "spe_gain": "SPE Gain Distribution",
    "dark_count_rate": "Dark Rate Distribution",
    "after_pulse_probability": "After Pulse Probability Distribution",
}

HIST_XRANGE = {
    "spe_gain": (0, 20),
    "dark_count_rate": (0, 5000),
    "after_pulse_probability": (0, 20),
}

st.header("📊 参数直方图")

if len(selected_run_ids) >= 2:
    compare_dfs = {}
    for rid in selected_run_ids:
        compare_dfs[rid] = filtered_df[filtered_df["run_id"] == rid]
    cols = st.columns(len(outlier_columns))
    for i, col_name in enumerate(outlier_columns):
        with cols[i]:
            fig = plot_histogram_compare(
                compare_dfs, col_name, nbins=bin_count,
                title=HIST_TITLES.get(col_name),
                x_range=HIST_XRANGE.get(col_name),
            )
            st.plotly_chart(fig, width="stretch", key=f"hist_cmp_{col_name}")
else:
    cols = st.columns(len(outlier_columns))
    for i, col_name in enumerate(outlier_columns):
        with cols[i]:
            outlier_col = f"{col_name}_outlier"
            mask = filtered_df[outlier_col] if outlier_col in filtered_df.columns else None
            fig = plot_histogram(
                filtered_df, col_name,
                nbins=bin_count, show_kde=show_kde,
                outlier_mask=mask,
                title=HIST_TITLES.get(col_name),
                x_range=HIST_XRANGE.get(col_name),
            )
            st.plotly_chart(fig, width="stretch", key=f"hist_{col_name}")

# ── 参数 vs PMT ID 趋势散点图 ───────────────────────────────────

st.header("📈 参数 vs. PMT ID 趋势散点图")

y_labels = {
    "spe_gain": "Gain [1.E6 e⁻]",
    "dark_count_rate": "Dark Rate [Hz]",
    "after_pulse_probability": "After Pulse Probability [%]",
}

if len(selected_run_ids) >= 2:
    compare_dfs = {}
    for rid in selected_run_ids:
        compare_dfs[rid] = filtered_df[filtered_df["run_id"] == rid]
    for col_name in outlier_columns:
        fig = plot_trend_compare(
            compare_dfs, col_name,
            center_method=center_method,
            y_label=y_labels.get(col_name, col_name),
        )
        st.plotly_chart(fig, width="stretch", key=f"trend_cmp_{col_name}")
else:
    for col_name in outlier_columns:
        outlier_col = f"{col_name}_outlier"
        mask = filtered_df[outlier_col] if outlier_col in filtered_df.columns else None
        fig = plot_trend_scatter(
            filtered_df, col_name,
            center_method=center_method,
            outlier_mask=mask,
            show_outlier_labels=enable_outlier,
            y_label=y_labels.get(col_name, col_name),
        )
        st.plotly_chart(fig, width="stretch", key=f"trend_{col_name}")

# ── 多 Run 对比控制 ─────────────────────────────────────────────

if len(selected_run_ids) >= 2:
    st.success(f"✅ 多 Run 对比模式已启用：同时对 {', '.join(selected_run_ids)} 进行对比")

# ── 3D 参数空间分布图 ───────────────────────────────────────────

st.header("🌐 三维参数空间分布图")

color_by_options = []
for opt in ["pmt_id", "run_id"]:
    if opt in filtered_df.columns:
        color_by_options.append(opt)
color_by = st.selectbox("颜色映射", options=color_by_options, index=0, key="color_by_3d") if color_by_options else None

if color_by and len(filtered_df) > 0:
    fig_3d = plot_3d_scatter(filtered_df, color_by=color_by)
    click_data = st.plotly_chart(fig_3d, width="stretch", key="3d_scatter")

    selected_points = st.session_state.get("3d_scatter", {}).get("selection", {}).get("points", [])
    if selected_points:
        st.subheader("📌 选中数据点详情")
        point_indices = []
        for p in selected_points:
            idx = p.get("point_index")
            if idx is not None and idx < len(filtered_df):
                point_indices.append(idx)
        if point_indices:
            st.dataframe(
                filtered_df.iloc[point_indices],
                width="stretch",
                hide_index=True,
            )
else:
    st.info("无可用数据或颜色映射字段缺失。")
