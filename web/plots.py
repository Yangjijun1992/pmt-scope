"""PMTscope 可视化模块 — 所有 Plotly 图表生成函数"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import compute_center, detect_outliers_df

LABELS = {
    "spe_gain": "Gain [1.E6 e⁻]",
    "dark_count_rate": "Dark Rate [Hz]",
    "after_pulse_probability": "APP [%]",
}

# ── 着色 / 形状 规则 ─────────────────────────────────────────────

DCR_LOW = 1000.0    # < 1000 Hz → blue
DCR_HIGH = 2000.0   # > 2000 Hz → red, 1000-2000 → orange-red

COLOR_LOW = "#2B6FB3"
COLOR_MID = "#E8652D"
COLOR_HIGH = "#D62728"
COLOR_GAIN = "#4C78A8"
COLOR_APP = "#4C78A8"
COLOR_HIGHLIGHT = "#9467BD"   # 紫色: 重复计数 PMT
COLOR_HIGHLIGHT_ER = "#2CA02C" # 绿色: 重复计数 PMT (energy_resolution)


def _scale_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column == "after_pulse_probability":
        return df[column] * 100
    return df[column]


def _format_value(column: str, value: float) -> str:
    if column == "spe_gain":
        return f"{value:.2f}"
    elif column == "dark_count_rate":
        return f"{value:.1f}"
    elif column == "after_pulse_probability":
        return f"{value:.4f}%"
    return f"{value:.3g}"


def _dcr_category(val: float) -> str:
    if val < DCR_LOW:
        return "low"
    elif val <= DCR_HIGH:
        return "mid"
    return "high"


def _dcr_color(val: float) -> str:
    cat = _dcr_category(val)
    return {"low": COLOR_LOW, "mid": COLOR_MID, "high": COLOR_HIGH}[cat]


def _dcr_marker(val: float) -> str:
    cat = _dcr_category(val)
    return {"low": "circle", "mid": "triangle-up", "high": "x"}[cat]


# ══════════════════════════════════════════════════════════════════
# 直方图
# ══════════════════════════════════════════════════════════════════


def plot_histogram(
    df: pd.DataFrame,
    column: str,
    nbins: int = 30,
    show_kde: bool = False,
    outlier_mask: Optional[pd.Series] = None,
    title: Optional[str] = None,
    x_range: Optional[Tuple[float, float]] = None,
) -> go.Figure:
    """绘制单参数直方图。

    dark_count_rate 使用三色分组（<1000 蓝 / 1000-2000 橙红 / >2000 红），
    标注 1000 Hz 虚线。
    after_pulse_probability 标注 5% 虚线。
    """
    if title is None:
        title = f"{column} 分布直方图"

    fig = go.Figure()

    # ── dark_count_rate: 三色分组 ──
    if column == "dark_count_rate":
        series = df[column].dropna()
        low = series[series < DCR_LOW]
        mid = series[(series >= DCR_LOW) & (series <= DCR_HIGH)]
        high = series[series > DCR_HIGH]

        for vals, color, label in [
            (low, COLOR_LOW, f"< {DCR_LOW:.0f} Hz  (n={len(low)})"),
            (mid, COLOR_MID, f"{DCR_LOW:.0f}–{DCR_HIGH:.0f} Hz  (n={len(mid)})"),
            (high, COLOR_HIGH, f"> {DCR_HIGH:.0f} Hz  (n={len(high)})"),
        ]:
            if len(vals) > 0:
                fig.add_trace(go.Histogram(x=vals, nbinsx=nbins, name=label,
                                           marker_color=color, opacity=0.85))

        fig.add_vline(x=DCR_LOW, line_dash="dash", line_color="#333333", line_width=3,
                      annotation_text=f"{DCR_LOW:.0f} Hz",
                      annotation_position="top right")

        y_title = "Counts"

    # ── after_pulse_probability: 单色 + 5% 虚线 ──
    elif column == "after_pulse_probability":
        series = _scale_column(df, column).dropna()
        fig.add_trace(go.Histogram(x=series, nbinsx=nbins, name="APP",
                                   marker_color=COLOR_APP, opacity=0.85))

        fig.add_vline(x=5.0, line_dash="dash", line_color="#D62728", line_width=3,
                      annotation_text="5%", annotation_position="top right")

        y_title = "Counts"

    # ── spe_gain: 单色，直接用原始值 ──
    else:
        vals = df[column].dropna()
        if outlier_mask is not None and len(outlier_mask) == len(df):
            normal_idx = df.index[~outlier_mask]
            outlier_idx = df.index[outlier_mask]
            normal_vals = df.loc[normal_idx, column].dropna()
            outlier_vals = df.loc[outlier_idx, column].dropna()
            if len(normal_vals) > 0:
                fig.add_trace(go.Histogram(x=normal_vals, nbinsx=nbins, name="正常", marker_color="steelblue"))
            if len(outlier_vals) > 0:
                fig.add_trace(go.Histogram(x=outlier_vals, nbinsx=nbins, name="离群点", marker_color="red"))
        else:
            fig.add_trace(go.Histogram(x=vals, nbinsx=nbins, name="分布", marker_color=COLOR_GAIN))

        y_title = "Counts"

    # KDE
    if show_kde and column != "dark_count_rate":
        raw = df[column].dropna() if column != "after_pulse_probability" else _scale_column(df, column).dropna()
        if len(raw) > 1:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(raw)
            x_kde = np.linspace(raw.min(), raw.max(), 200)
            kde_y = kde(x_kde)
            scale = len(raw) * (raw.max() - raw.min()) / nbins
            fig.add_trace(go.Scatter(x=x_kde, y=kde_y * scale, mode="lines",
                                     name="KDE", line=dict(color="orange", width=2)))

    layout_kwargs = dict(
        title=title,
        xaxis_title=LABELS.get(column, column),
        yaxis_title=y_title,
        bargap=0.05,
        template="plotly_white",
    )
    if x_range:
        layout_kwargs["xaxis"] = dict(range=x_range)

    if column in ("spe_gain", "dark_count_rate", "after_pulse_probability"):
        layout_kwargs["xaxis"] = dict(
            title=dict(text=LABELS.get(column, column), standoff=0),
            side="bottom",
        )
        layout_kwargs["xaxis_title_standoff"] = 0

    fig.update_layout(**layout_kwargs)
    return fig


def plot_histogram_compare(
    dfs: Dict[str, pd.DataFrame],
    column: str,
    nbins: int = 30,
    title: Optional[str] = None,
    x_range: Optional[Tuple[float, float]] = None,
) -> go.Figure:
    """多 Run 对比直方图。"""
    if title is None:
        title = f"{column} 多 Run 对比直方图"

    fig = go.Figure()
    for label, df in dfs.items():
        series = _scale_column(df, column).dropna()
        if len(series) > 0:
            fig.add_trace(go.Histogram(x=series, nbinsx=nbins, name=str(label), opacity=0.6))

    layout_kwargs = dict(
        title=title,
        xaxis_title=LABELS.get(column, column),
        yaxis_title="Counts",
        bargap=0.05,
        barmode="overlay",
        template="plotly_white",
    )
    if x_range:
        layout_kwargs["xaxis"] = dict(range=x_range)
    fig.update_layout(**layout_kwargs)
    return fig


# ══════════════════════════════════════════════════════════════════
# 3D 散点图
# ══════════════════════════════════════════════════════════════════


def plot_3d_scatter(
    df: pd.DataFrame,
    color_by: str = "pmt_id",
    title: str = "三维参数空间分布",
) -> go.Figure:
    """绘制三维参数空间散点图。

    只展示有 after_pulse_probability 数据的 PMT，
    按 pmt_id 聚合取均值后展示 spe_gain / dark_count_rate / after_pulse_probability。
    """
    ap_df = df[df["after_pulse_probability"].notna()].copy()
    pmt_ids_with_ap = ap_df["pmt_id"].unique()
    plot_df = df[df["pmt_id"].isin(pmt_ids_with_ap)].copy()

    agg = plot_df.groupby("pmt_id", as_index=False).agg({
        "spe_gain": "mean",
        "dark_count_rate": "mean",
        "after_pulse_probability": "mean",
    })
    agg["after_pulse_probability"] = agg["after_pulse_probability"] * 100

    # merge back extra columns for hover
    extra_cols = ["run_id", "hv", "temperature", "notes"]
    for c in extra_cols:
        if c in plot_df.columns:
            latest = plot_df.groupby("pmt_id")[c].last().reset_index()
            agg = agg.merge(latest, on="pmt_id", how="left")

    plot_df = agg

    fig = px.scatter_3d(
        plot_df,
        x="spe_gain",
        y="dark_count_rate",
        z="after_pulse_probability",
        color=color_by,
        title=title,
        labels={
            "spe_gain": "Gain [1.E6 e⁻]",
            "dark_count_rate": "Dark Rate [Hz]",
            "after_pulse_probability": "After Pulse Probability [%]",
        },
        opacity=0.8,
        custom_data=["pmt_id", "run_id", "hv"] if all(c in plot_df.columns for c in ["pmt_id", "run_id", "hv"]) else None,
    )
    fig.update_traces(
        hovertemplate=(
            "Gain: %{x:.2f} [e⁻]<br>"
            "Dark Rate: %{y:.1f} [Hz]<br>"
            "After Pulse: %{z:.4f} [%]<br>"
            "pmt_id: %{customdata[0]}<br>"
            "run_id: %{customdata[1]}<br>"
            "hv: %{customdata[2]}<extra></extra>"
        ),
        marker=dict(size=5),
    )
    fig.update_layout(
        template="plotly_white",
        legend=dict(title=dict(text="pmt_id")),
    )
    return fig


# ══════════════════════════════════════════════════════════════════
# 趋势散点图 (参数 vs PMT ID)
# ══════════════════════════════════════════════════════════════════


def plot_trend_scatter(
    df: pd.DataFrame,
    y_column: str,
    center_method: str = "median",
    outlier_mask: Optional[pd.Series] = None,
    show_outlier_labels: bool = True,
    title: Optional[str] = None,
    y_label: Optional[str] = None,
    highlight_pmts: Optional[set] = None,
) -> go.Figure:
    """参数 vs. PMT ID 趋势散点图。

    spe_gain: xr ▲ / westlake ●，过滤 hv>800V，离群点 >3σ 标注。
    dark_count_rate: <1000蓝/1000-2000橙/>2000红，xr■/westlake●，1000Hz虚线。
    westlake DCR 同一 pmt_id 只保留最小值。
    after_pulse_probability: 正常+离群点，保持不变。
    energy_resolution: 按 xr/westlake 区分，0.5 阈值虚线。
    """
    import re as _re

    if title is None:
        title = f"{y_column} vs PMT ID"
    if y_label is None:
        y_label = LABELS.get(y_column, y_column)

    valid = df[y_column].notna()
    plot_df = df[valid].copy()

    if "run_id" in plot_df.columns:
        plot_df["_run_type"] = plot_df["run_id"].apply(
            lambda x: "xr" if _re.match(r"^xr", str(x)) else "numeric"
        )
    else:
        plot_df["_run_type"] = "numeric"

    cd_cols = [c for c in ["run_id", "hv", "temperature", "notes"] if c in plot_df.columns]

    if y_column == "spe_gain":
        plot_df = plot_df[plot_df.get("hv", 0) <= 800].copy()
        plot_df.sort_values("pmt_id", inplace=True)
        center_val = compute_center(plot_df[y_column], method=center_method)

        mean_val = plot_df[y_column].mean()
        std_val = plot_df[y_column].std()
        lower = mean_val - 3 * std_val
        upper = mean_val + 3 * std_val
        plot_df["_outlier"] = (plot_df[y_column] < lower) | (plot_df[y_column] > upper)
        normal = plot_df[~plot_df["_outlier"]]
        outlier = plot_df[plot_df["_outlier"]]

        if highlight_pmts is None:
            highlight_pmts = set()

        fig = go.Figure()
        for sub, marker, color, label_tag in [
            (normal[normal["_run_type"] == "xr"], "triangle-up", "#D62728", "xr tested"),
            (normal[(normal["_run_type"] == "numeric") & (~normal["pmt_id"].isin(highlight_pmts))],
             "circle", "#2B6FB3", "westlake tested"),
            (normal[(normal["_run_type"] == "numeric") & (normal["pmt_id"].isin(highlight_pmts))],
             "circle-open", COLOR_HIGHLIGHT, "overlap (xr + westlake)"),
        ]:
            if len(sub) == 0:
                continue
            cd = sub[cd_cols].fillna("").values
            fig.add_trace(go.Scatter(
                x=sub["pmt_id"].astype(str), y=sub[y_column],
                mode="markers", name=label_tag,
                marker=dict(color=color, symbol=marker, size=11, line=dict(width=2, color=color)),
                customdata=cd,
                hovertemplate=(
                    f"pmt_id: %{{x}}<br>{y_label}: %{{y:.2f}}<br>"
                    "run_id: %{customdata[0]}<br>"
                    "hv: %{customdata[1]}<br>"
                    "notes: %{customdata[3]}<extra></extra>"
                ),
            ))
        if len(outlier) > 0:
            cd = outlier[cd_cols].fillna("").values
            fig.add_trace(go.Scatter(
                x=outlier["pmt_id"].astype(str), y=outlier[y_column],
                mode="markers+text", name="Outlier (&gt;3σ)",
                marker=dict(color="#D62728", symbol="x", size=14, line=dict(width=2, color="#D62728")),
                text=outlier["pmt_id"].astype(str),
                textposition="top center",
                textfont=dict(color="#D62728", size=9),
                customdata=cd,
                hovertemplate=(
                    f"pmt_id: %{{x}}<br>{y_label}: %{{y:.2f}}<br>"
                    "run_id: %{customdata[0]}<br>"
                    "hv: %{customdata[1]}<br>"
                    "notes: %{customdata[3]}<extra></extra>"
                ),
            ))
        fig.add_hline(y=center_val, line_dash="dash", line_color="gray", line_width=2,
                      annotation_text=f"median: {center_val:.2f}", annotation_position="top right")

    elif y_column == "dark_count_rate":
        xr_df = plot_df[plot_df["_run_type"] == "xr"]
        num_df = plot_df[plot_df["_run_type"] == "numeric"]
        if len(num_df) > 0:
            num_df = num_df.loc[num_df.groupby("pmt_id")[y_column].idxmin()]
        plot_df = pd.concat([xr_df, num_df], ignore_index=True)
        plot_df.sort_values("pmt_id", inplace=True)

        if highlight_pmts is None:
            highlight_pmts = set()

        fig = go.Figure()
        for mask_fn, color, dcr_label in [
            (lambda v: v < DCR_LOW, COLOR_LOW, f"&lt; {DCR_LOW:.0f} Hz"),
            (lambda v: (v >= DCR_LOW) & (v <= DCR_HIGH), COLOR_MID, f"{DCR_LOW:.0f}–{DCR_HIGH:.0f} Hz"),
            (lambda v: v > DCR_HIGH, COLOR_HIGH, f"&gt; {DCR_HIGH:.0f} Hz"),
        ]:
            sub = plot_df[mask_fn(plot_df[y_column])]
            is_high = dcr_label.startswith("&gt;")
            for rt, symbol, rt_label in [("xr", "square", "xr tested"), ("numeric", "circle", "westlake tested")]:
                sub_rt = sub[sub["_run_type"] == rt]
                if len(sub_rt) == 0:
                    continue
                sub_hl = sub_rt[sub_rt["pmt_id"].isin(highlight_pmts)]
                sub_norm = sub_rt[~sub_rt["pmt_id"].isin(highlight_pmts)]
                marker_color = COLOR_HIGHLIGHT if len(sub_hl) > 0 and rt == "numeric" else color
                marker_symbol = "diamond-open" if len(sub_hl) > 0 and rt == "numeric" else symbol
                if len(sub_hl) > 0 and rt == "numeric":
                    sub_hl_label = f"{dcr_label} – overlap (n={len(sub_hl)})"
                    cd = sub_hl[cd_cols].fillna("").values
                    fig.add_trace(go.Scatter(
                        x=sub_hl["pmt_id"].astype(str), y=sub_hl[y_column],
                        mode="markers+text" if is_high else "markers",
                        name=sub_hl_label,
                        marker=dict(color=COLOR_HIGHLIGHT, symbol="diamond-open", size=12, line=dict(width=2, color=COLOR_HIGHLIGHT)),
                        text=sub_hl["pmt_id"].astype(str) if is_high else None,
                        textposition="top center", textfont=dict(color=COLOR_HIGHLIGHT, size=9),
                        customdata=cd,
                        hovertemplate=(
                            f"pmt_id: %{{x}}<br>{y_label}: %{{y:.1f}}<br>"
                            "run_id: %{customdata[0]}<br>"
                            "hv: %{customdata[1]}<br>"
                            "notes: %{customdata[3]}<extra></extra>"
                        ),
                    ))
                if len(sub_norm) > 0:
                    cd = sub_norm[cd_cols].fillna("").values
                    fig.add_trace(go.Scatter(
                        x=sub_norm["pmt_id"].astype(str), y=sub_norm[y_column],
                        mode="markers+text" if is_high else "markers",
                        name=f"{dcr_label} – {rt_label} (n={len(sub_norm)})",
                        marker=dict(color=marker_color, symbol=marker_symbol, size=9, line=dict(width=1, color=marker_color)),
                        text=sub_norm["pmt_id"].astype(str) if is_high else None,
                        textposition="top center", textfont=dict(color=marker_color, size=9),
                        customdata=cd,
                        hovertemplate=(
                            f"pmt_id: %{{x}}<br>{y_label}: %{{y:.1f}}<br>"
                            "run_id: %{customdata[0]}<br>"
                            "hv: %{customdata[1]}<br>"
                            "notes: %{customdata[3]}<extra></extra>"
                        ),
                    ))
        fig.add_hline(y=DCR_LOW, line_dash="dash", line_color="gray", line_width=2,
                      annotation_text=f"{DCR_LOW:.0f} Hz", annotation_position="top right")

    elif y_column == "energy_resolution":
        plot_df.sort_values("pmt_id", inplace=True)
        center_val = compute_center(plot_df[y_column], method=center_method)

        if highlight_pmts is None:
            highlight_pmts = set()

        fig = go.Figure()
        for rt, marker, color, label_tag in [
            ("xr", "square", "#D62728", "xr tested"),
            ("numeric", "circle", "#2B6FB3", "westlake tested"),
        ]:
            sub = plot_df[plot_df["_run_type"] == rt]
            if len(sub) == 0:
                continue
            sub_hl = sub[sub["pmt_id"].isin(highlight_pmts)]
            sub_norm = sub[~sub["pmt_id"].isin(highlight_pmts)]
            if rt == "numeric" and len(sub_hl) > 0:
                cd = sub_hl[cd_cols].fillna("").values
                fig.add_trace(go.Scatter(
                    x=sub_hl["pmt_id"].astype(str), y=sub_hl[y_column],
                    mode="markers", name="overlap (xr + westlake)",
                    marker=dict(color=COLOR_HIGHLIGHT_ER, symbol="circle-open", size=12, line=dict(width=2, color=COLOR_HIGHLIGHT_ER)),
                    customdata=cd,
                    hovertemplate=(
                        f"pmt_id: %{{x}}<br>{y_label}: %{{y:.4f}}<br>"
                        "run_id: %{customdata[0]}<br>"
                        "hv: %{customdata[1]}<br>"
                        "notes: %{customdata[3]}<extra></extra>"
                    ),
                ))
            if len(sub_norm) > 0:
                cd = sub_norm[cd_cols].fillna("").values
                fig.add_trace(go.Scatter(
                    x=sub_norm["pmt_id"].astype(str), y=sub_norm[y_column],
                    mode="markers", name=label_tag,
                    marker=dict(color=color, symbol=marker, size=9, line=dict(width=1, color=color)),
                    customdata=cd,
                    hovertemplate=(
                        f"pmt_id: %{{x}}<br>{y_label}: %{{y:.4f}}<br>"
                        "run_id: %{customdata[0]}<br>"
                        "hv: %{customdata[1]}<br>"
                        "notes: %{customdata[3]}<extra></extra>"
                    ),
                ))
        fig.add_hline(y=0.5, line_dash="dash", line_color="#D62728", line_width=2,
                      annotation_text="Threshold: 0.5", annotation_position="top right")
        fig.add_hline(y=center_val, line_dash="dot", line_color="gray", line_width=1,
                      annotation_text=f"median: {center_val:.4f}", annotation_position="top right")

    else:
        plot_df["app_pct"] = plot_df[y_column] * 100
        center_val = compute_center(plot_df["app_pct"], method=center_method)
        normal = plot_df.copy()
        outlier = pd.DataFrame()
        if highlight_pmts is None:
            highlight_pmts = set()

        if outlier_mask is not None and len(outlier_mask) == len(plot_df):
            outlier = plot_df[outlier_mask.loc[plot_df.index].values]
            normal = plot_df[~outlier_mask.loc[plot_df.index].values]

        fig = go.Figure()
        # 正常 non-highlight
        norm_nohl = normal[~normal["pmt_id"].isin(highlight_pmts)]
        cd_n = norm_nohl[cd_cols].fillna("").values
        fig.add_trace(go.Scatter(
            x=norm_nohl["pmt_id"].astype(str), y=norm_nohl["app_pct"],
            mode="markers", name="正常",
            marker=dict(color=COLOR_GAIN, size=8),
            customdata=cd_n,
            hovertemplate=(
                f"pmt_id: %{{x}}<br>{y_label}: %{{y:.2f}}%<br>"
                "run_id: %{customdata[0]}<br>"
                "notes: %{customdata[3]}<extra></extra>"
            ),
        ))
        # 正常 highlight
        norm_hl = normal[normal["pmt_id"].isin(highlight_pmts)]
        if len(norm_hl) > 0:
            cd_hl = norm_hl[cd_cols].fillna("").values
            fig.add_trace(go.Scatter(
                x=norm_hl["pmt_id"].astype(str), y=norm_hl["app_pct"],
                mode="markers", name="overlap (xr + westlake)",
                marker=dict(color=COLOR_HIGHLIGHT, symbol="diamond-open", size=12, line=dict(width=2, color=COLOR_HIGHLIGHT)),
                customdata=cd_hl,
                hovertemplate=(
                    f"pmt_id: %{{x}}<br>{y_label}: %{{y:.2f}}%<br>"
                    "run_id: %{customdata[0]}<br>"
                    "notes: %{customdata[3]}<extra></extra>"
                ),
            ))
        if len(outlier) > 0:
            outlier_nohl = outlier[~outlier["pmt_id"].isin(highlight_pmts)]
            if len(outlier_nohl) > 0:
                cd_o = outlier_nohl[cd_cols].fillna("").values
                fig.add_trace(go.Scatter(
                    x=outlier_nohl["pmt_id"].astype(str), y=outlier_nohl["app_pct"],
                    mode="markers+text" if show_outlier_labels else "markers",
                    name="离群点",
                    marker=dict(color=COLOR_HIGH, size=12, symbol="x", line=dict(width=2, color=COLOR_HIGH)),
                    text=outlier_nohl["pmt_id"].astype(str) if show_outlier_labels else None,
                    textposition="top center", textfont=dict(color=COLOR_HIGH, size=9),
                    customdata=cd_o,
                    hovertemplate=(
                        f"pmt_id: %{{x}}<br>{y_label}: %{{y:.2f}}%<br>"
                        "run_id: %{customdata[0]}<br>"
                        "notes: %{customdata[3]}<extra></extra>"
                    ),
                ))
        fig.add_hline(y=center_val, line_dash="dash", line_color="gray", line_width=2,
                      annotation_text=f"{center_method}: {center_val:.3g}", annotation_position="top right")

    fig.update_layout(
        title=title,
        xaxis_title="PMT ID",
        yaxis_title=y_label,
        template="plotly_white",
        xaxis=dict(tickangle=45),
    )
    return fig


def plot_trend_compare(
    dfs: Dict[str, pd.DataFrame],
    y_column: str,
    center_method: str = "median",
    title: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """多 Run 对比趋势散点图。"""
    if title is None:
        title = f"{y_column} vs PMT ID (多 Run 对比)"
    if y_label is None:
        y_label = LABELS.get(y_column, y_column)

    fig = go.Figure()
    symbols = ["circle", "diamond", "square", "triangle-up", "cross", "x"]
    colors = px.colors.qualitative.Plotly

    for i, (label, df) in enumerate(dfs.items()):
        series = _scale_column(df, y_column).dropna()
        center_val = compute_center(series, method=center_method)
        valid = df[y_column].notna()
        plot_df = df[valid].copy()

        display_y = _scale_column(plot_df, y_column)
        color = colors[i % len(colors)]
        symbol = symbols[i % len(symbols)]
        customdata = plot_df[["run_id", "hv", "temperature", "notes"]].fillna("").values
        fig.add_trace(go.Scatter(
            x=plot_df["pmt_id"].astype(str),
            y=display_y,
            mode="markers",
            name=f"{label}",
            marker=dict(color=color, symbol=symbol, size=8),
            customdata=customdata,
            hovertemplate=(
                f"pmt_id: %{{x}}<br>"
                f"{y_label}: %{{y}}<br>"
                "run_id: %{customdata[0]}<br>"
                "hv: %{customdata[1]}<br>"
                "temperature: %{customdata[2]}<br>"
                "notes: %{customdata[3]}<extra></extra>"
            ),
        ))
        fig.add_hline(
            y=center_val, line_dash="dash", line_color=color, opacity=0.5,
            annotation_text=f"{label} {center_method}: {center_val:.3g}",
            annotation_position=f"top {'right' if i < 3 else 'left'}",
        )

    fig.update_layout(
        title=title,
        xaxis_title="PMT ID",
        yaxis_title=y_label,
        template="plotly_white",
        xaxis=dict(tickangle=45),
    )
    return fig
