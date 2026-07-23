"""PMTscope 可视化模块 — 所有 Plotly 图表生成函数"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import compute_center, detect_outliers_df


def plot_histogram(
    df: pd.DataFrame,
    column: str,
    nbins: int = 30,
    show_kde: bool = False,
    outlier_mask: pd.Series | None = None,
    title: str | None = None,
) -> go.Figure:
    """绘制单参数直方图，支持 KDE 叠加和离群点高亮。"""
    series = df[column].dropna()
    if title is None:
        title = f"{column} 分布直方图"

    fig = go.Figure()

    if outlier_mask is not None and len(outlier_mask) == len(df):
        normal_idx = df.index[~outlier_mask]
        outlier_idx = df.index[outlier_mask]
        normal_vals = df.loc[normal_idx.intersection(series.index), column]
        outlier_vals = df.loc[outlier_idx.intersection(series.index), column]
        if len(normal_vals) > 0:
            fig.add_trace(go.Histogram(x=normal_vals, nbinsx=nbins, name="正常", marker_color="steelblue"))
        if len(outlier_vals) > 0:
            fig.add_trace(go.Histogram(x=outlier_vals, nbinsx=nbins, name="离群点", marker_color="red"))
    else:
        fig.add_trace(go.Histogram(x=series, nbinsx=nbins, name="分布", marker_color="steelblue"))

    if show_kde and len(series) > 1:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(series)
        x_range = np.linspace(series.min(), series.max(), 200)
        kde_y = kde(x_range)
        scale = len(series) * (series.max() - series.min()) / nbins
        fig.add_trace(go.Scatter(x=x_range, y=kde_y * scale, mode="lines", name="KDE", line=dict(color="orange", width=2)))

    fig.update_layout(
        title=title,
        xaxis_title=column,
        yaxis_title="频次",
        bargap=0.05,
        template="plotly_white",
    )
    return fig


def plot_histogram_compare(
    dfs: dict[str, pd.DataFrame],
    column: str,
    nbins: int = 30,
    title: str | None = None,
) -> go.Figure:
    """多 Run 对比直方图。"""
    if title is None:
        title = f"{column} 多 Run 对比直方图"

    fig = go.Figure()
    for label, df in dfs.items():
        series = df[column].dropna()
        if len(series) > 0:
            fig.add_trace(go.Histogram(x=series, nbinsx=nbins, name=str(label), opacity=0.6))

    fig.update_layout(
        title=title,
        xaxis_title=column,
        yaxis_title="频次",
        bargap=0.05,
        barmode="overlay",
        template="plotly_white",
    )
    return fig


def plot_3d_scatter(
    df: pd.DataFrame,
    color_by: str = "pmt_id",
    title: str = "三维参数空间分布",
) -> go.Figure:
    """绘制三维参数空间散点图。"""
    subset = df[["spe_gain", "dark_count_rate", "after_pulse_probability", color_by]].dropna()
    if "id" in df.columns:
        subset["id"] = df.loc[subset.index, "id"]
        subset["pmt_id"] = df.loc[subset.index, "pmt_id"]
        subset["run_id"] = df.loc[subset.index, "run_id"]
        subset["hv"] = df.loc[subset.index, "hv"]
    else:
        for col in ["pmt_id", "run_id", "hv"]:
            if col in df.columns:
                subset[col] = df.loc[subset.index, col]

    fig = px.scatter_3d(
        subset,
        x="spe_gain",
        y="dark_count_rate",
        z="after_pulse_probability",
        color=color_by,
        title=title,
        labels={
            "spe_gain": "单光子增益",
            "dark_count_rate": "暗计数率 (Hz)",
            "after_pulse_probability": "后脉冲概率",
        },
        opacity=0.8,
        custom_data=["pmt_id", "run_id", "hv"] if all(c in subset.columns for c in ["pmt_id", "run_id", "hv"]) else None,
    )
    fig.update_traces(
        hovertemplate=(
            "spe_gain: %{x}<br>"
            "dark_count_rate: %{y}<br>"
            "after_pulse_probability: %{z}<br>"
            "pmt_id: %{customdata[0]}<br>"
            "run_id: %{customdata[1]}<br>"
            "hv: %{customdata[2]}<extra></extra>"
        ),
        marker=dict(size=5),
    )
    fig.update_layout(template="plotly_white")
    return fig


def plot_trend_scatter(
    df: pd.DataFrame,
    y_column: str,
    center_method: str = "median",
    outlier_mask: pd.Series | None = None,
    show_outlier_labels: bool = True,
    title: str | None = None,
    y_label: str | None = None,
) -> go.Figure:
    """绘制参数 vs. PMT ID 趋势散点图。"""
    if title is None:
        title = f"{y_column} vs PMT ID"
    if y_label is None:
        y_label = y_column

    series = df[y_column].dropna()
    center_val = compute_center(series, method=center_method)  # type: ignore[arg-type]
    valid = df[y_column].notna()
    plot_df = df[valid].copy()
    plot_df["_pmt_sort"] = pd.to_numeric(plot_df["pmt_id"], errors="coerce")
    if plot_df["_pmt_sort"].notna().all():
        plot_df = plot_df.sort_values("_pmt_sort")
    else:
        plot_df = plot_df.sort_values("pmt_id")

    fig = go.Figure()

    normal = plot_df.copy()
    outlier = pd.DataFrame()
    if outlier_mask is not None and len(outlier_mask) == len(plot_df):
        outlier = plot_df[outlier_mask.loc[plot_df.index].values]
        normal = plot_df[~outlier_mask.loc[plot_df.index].values]

    fig.add_trace(go.Scatter(
        x=normal["pmt_id"].astype(str),
        y=normal[y_column],
        mode="markers",
        name="正常",
        marker=dict(color="steelblue", size=8),
        customdata=normal[["run_id", "hv", "temperature", "notes"]].fillna("").values,
        hovertemplate=(
            f"pmt_id: %{{x}}<br>"
            f"{y_column}: %{{y}}<br>"
            "run_id: %{customdata[0]}<br>"
            "hv: %{customdata[1]}<br>"
            "temperature: %{customdata[2]}<br>"
            "notes: %{customdata[3]}<extra></extra>"
        ),
    ))

    if len(outlier) > 0:
        outlier_x = outlier["pmt_id"].astype(str)
        outlier_y = outlier[y_column]
        fig.add_trace(go.Scatter(
            x=outlier_x,
            y=outlier_y,
            mode="markers+text" if show_outlier_labels else "markers",
            name="离群点",
            marker=dict(color="red", size=10, symbol="x"),
            text=outlier["pmt_id"].astype(str) if show_outlier_labels else None,
            textposition="top center",
            textfont=dict(color="red", size=10),
            customdata=outlier[["run_id", "hv", "temperature", "notes"]].fillna("").values,
            hovertemplate=(
                f"pmt_id: %{{x}}<br>"
                f"{y_column}: %{{y}}<br>"
                "run_id: %{customdata[0]}<br>"
                "hv: %{customdata[1]}<br>"
                "temperature: %{customdata[2]}<br>"
                "notes: %{customdata[3]}<extra></extra>"
            ),
        ))

    fig.add_hline(
        y=center_val, line_dash="dash", line_color="gray",
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
    dfs: dict[str, pd.DataFrame],
    y_column: str,
    center_method: str = "median",
    title: str | None = None,
    y_label: str | None = None,
) -> go.Figure:
    """多 Run 对比趋势散点图。"""
    if title is None:
        title = f"{y_column} vs PMT ID (多 Run 对比)"
    if y_label is None:
        y_label = y_column

    fig = go.Figure()
    symbols = ["circle", "diamond", "square", "triangle-up", "cross", "x"]
    colors = px.colors.qualitative.Plotly

    for i, (label, df) in enumerate(dfs.items()):
        series = df[y_column].dropna()
        center_val = compute_center(series, method=center_method)  # type: ignore[arg-type]
        valid = df[y_column].notna()
        plot_df = df[valid].copy()

        color = colors[i % len(colors)]
        symbol = symbols[i % len(symbols)]
        fig.add_trace(go.Scatter(
            x=plot_df["pmt_id"].astype(str),
            y=plot_df[y_column],
            mode="markers",
            name=f"{label}",
            marker=dict(color=color, symbol=symbol, size=8),
            customdata=plot_df[["run_id", "hv", "temperature", "notes"]].fillna("").values,
            hovertemplate=(
                f"pmt_id: %{{x}}<br>"
                f"{y_column}: %{{y}}<br>"
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
