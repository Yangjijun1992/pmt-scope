"""PMTscope 可视化模块 — 所有 Plotly 图表生成函数"""

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
    """绘制三维参数空间散点图。"""
    plot_df = df[["spe_gain", "dark_count_rate", "after_pulse_probability", color_by]].dropna().copy()
    plot_df["after_pulse_probability"] = plot_df["after_pulse_probability"] * 100

    for col in ["pmt_id", "run_id", "hv"]:
        if col in df.columns:
            plot_df[col] = df.loc[plot_df.index, col]

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
) -> go.Figure:
    """绘制参数 vs. PMT ID 趋势散点图。

    dark_count_rate 使用三种形状（圆/三角形/叉号），>2000 Hz 标注 pmt_id。
    """
    if title is None:
        title = f"{y_column} vs PMT ID"
    if y_label is None:
        y_label = LABELS.get(y_column, y_column)

    valid = df[y_column].notna()
    plot_df = df[valid].copy()
    plot_df = plot_df.sort_values("pmt_id")

    fig = go.Figure()

    series = _scale_column(plot_df, y_column).dropna()
    center_val = compute_center(series, method=center_method)
    display_y = _scale_column(plot_df, y_column)

    # ── dark_count_rate: 三分组形状 ──
    if y_column == "dark_count_rate":
        for mask_fn, color, marker, label in [
            (lambda v: v < DCR_LOW, COLOR_LOW, "circle", f"< {DCR_LOW:.0f} Hz"),
            (lambda v: (v >= DCR_LOW) & (v <= DCR_HIGH), COLOR_MID, "triangle-up", f"{DCR_LOW:.0f}–{DCR_HIGH:.0f} Hz"),
            (lambda v: v > DCR_HIGH, COLOR_HIGH, "x", f"> {DCR_HIGH:.0f} Hz"),
        ]:
            subset = plot_df[mask_fn(plot_df[y_column])].copy()
            if len(subset) == 0:
                continue
            sy = _scale_column(subset, y_column)
            cd = subset[["run_id", "hv", "temperature", "notes"]].fillna("").values
            is_high = label.startswith(">")
            fig.add_trace(go.Scatter(
                x=subset["pmt_id"].astype(str),
                y=sy,
                mode="markers+text" if is_high else "markers",
                name=label,
                marker=dict(color=color, symbol=marker, size=10, line=dict(width=1, color=color)),
                text=subset["pmt_id"].astype(str) if is_high else None,
                textposition="top center",
                textfont=dict(color=color, size=9),
                customdata=cd,
                hovertemplate=(
                    f"pmt_id: %{{x}}<br>"
                    f"{y_label}: %{{y:.1f}}<br>"
                    "run_id: %{customdata[0]}<br>"
                    "hv: %{customdata[1]}<br>"
                    "temperature: %{customdata[2]}<br>"
                    "notes: %{customdata[3]}<extra></extra>"
                ),
            ))

    # ── spe_gain / after_pulse_probability: 正常 + 离群点 ──
    else:
        normal = plot_df.copy()
        outlier = pd.DataFrame()
        if outlier_mask is not None and len(outlier_mask) == len(plot_df):
            outlier = plot_df[outlier_mask.loc[plot_df.index].values]
            normal = plot_df[~outlier_mask.loc[plot_df.index].values]

        normal_y = _scale_column(normal, y_column)
        customdata_n = normal[["run_id", "hv", "temperature", "notes"]].fillna("").values
        fig.add_trace(go.Scatter(
            x=normal["pmt_id"].astype(str),
            y=normal_y,
            mode="markers",
            name="正常",
            marker=dict(color=COLOR_GAIN, size=8),
            customdata=customdata_n,
            hovertemplate=(
                f"pmt_id: %{{x}}<br>"
                f"{y_label}: %{{y}}<br>"
                "run_id: %{customdata[0]}<br>"
                "hv: %{customdata[1]}<br>"
                "temperature: %{customdata[2]}<br>"
                "notes: %{customdata[3]}<extra></extra>"
            ),
        ))

        if len(outlier) > 0:
            outlier_y_scaled = _scale_column(outlier, y_column)
            customdata_o = outlier[["run_id", "hv", "temperature", "notes"]].fillna("").values
            fig.add_trace(go.Scatter(
                x=outlier["pmt_id"].astype(str),
                y=outlier_y_scaled,
                mode="markers+text" if show_outlier_labels else "markers",
                name="离群点",
                marker=dict(color=COLOR_HIGH, size=12, symbol="x", line=dict(width=2, color=COLOR_HIGH)),
                text=outlier["pmt_id"].astype(str) if show_outlier_labels else None,
                textposition="top center",
                textfont=dict(color=COLOR_HIGH, size=9),
                customdata=customdata_o,
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
        y=center_val, line_dash="dash", line_color="gray", line_width=2,
        annotation_text=f"{center_method}: {center_val:.3g}",
        annotation_position="top right",
    )

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
