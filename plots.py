"""PMTscope 可视化模块 — 所有 Plotly 图表生成函数"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import compute_center, detect_outliers_df

LABELS = {
    "spe_gain": "Gain [1.E6 e⁻]",
    "dark_count_rate": "Dark Rate [Hz]",
    "after_pulse_probability": "After Pulse Probability [%]",
}


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


def plot_histogram(
    df: pd.DataFrame,
    column: str,
    nbins: int = 30,
    show_kde: bool = False,
    outlier_mask: pd.Series | None = None,
    title: str | None = None,
    x_range: tuple[float, float] | None = None,
) -> go.Figure:
    """绘制单参数直方图，支持 KDE 叠加和离群点高亮。"""
    series = _scale_column(df, column).dropna()
    if title is None:
        title = f"{column} 分布直方图"

    fig = go.Figure()

    if outlier_mask is not None and len(outlier_mask) == len(df):
        normal_idx = df.index[~outlier_mask]
        outlier_idx = df.index[outlier_mask]
        normal_vals = _scale_column(df.loc[normal_idx.intersection(series.index)], column).dropna()
        outlier_vals = _scale_column(df.loc[outlier_idx.intersection(series.index)], column).dropna()
        if len(normal_vals) > 0:
            fig.add_trace(go.Histogram(x=normal_vals, nbinsx=nbins, name="正常", marker_color="steelblue"))
        if len(outlier_vals) > 0:
            fig.add_trace(go.Histogram(x=outlier_vals, nbinsx=nbins, name="离群点", marker_color="red"))
    else:
        fig.add_trace(go.Histogram(x=series, nbinsx=nbins, name="分布", marker_color="steelblue"))

    if show_kde and len(series) > 1:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(series)
        x_range_kde = np.linspace(series.min(), series.max(), 200)
        kde_y = kde(x_range_kde)
        scale = len(series) * (series.max() - series.min()) / nbins
        fig.add_trace(go.Scatter(x=x_range_kde, y=kde_y * scale, mode="lines", name="KDE", line=dict(color="orange", width=2)))

    layout_kwargs = dict(
        title=title,
        xaxis_title=LABELS.get(column, column),
        yaxis_title="频次",
        bargap=0.05,
        template="plotly_white",
    )
    if x_range:
        layout_kwargs["xaxis"] = dict(range=x_range)
    fig.update_layout(**layout_kwargs)
    return fig


def plot_histogram_compare(
    dfs: dict[str, pd.DataFrame],
    column: str,
    nbins: int = 30,
    title: str | None = None,
    x_range: tuple[float, float] | None = None,
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
        yaxis_title="频次",
        bargap=0.05,
        barmode="overlay",
        template="plotly_white",
    )
    if x_range:
        layout_kwargs["xaxis"] = dict(range=x_range)
    fig.update_layout(**layout_kwargs)
    return fig


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
            "Gain: %{x:.2f} [1.E6 e⁻]<br>"
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


def _trend_figure(
    plot_df: pd.DataFrame,
    y_column: str,
    y_label: str,
    center_method: str,
) -> go.Figure:
    fig = go.Figure()
    series = _scale_column(plot_df, y_column).dropna()
    center_val = compute_center(series, method=center_method)

    display_y = _scale_column(plot_df, y_column)
    x_vals = plot_df["pmt_id"].astype(str)
    customdata = plot_df[["run_id", "hv", "temperature", "notes"]].fillna("").values

    fig.add_trace(go.Scatter(
        x=x_vals, y=display_y,
        mode="markers",
        name="数据点",
        marker=dict(color="steelblue", size=8),
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
        y=center_val, line_dash="dash", line_color="gray",
        annotation_text=f"{center_method}: {center_val:.3g}",
        annotation_position="top right",
    )

    fig.update_layout(
        xaxis_title="PMT ID",
        yaxis_title=y_label,
        template="plotly_white",
        xaxis=dict(tickangle=45),
    )
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
        y_label = LABELS.get(y_column, y_column)

    valid = df[y_column].notna()
    plot_df = df[valid].copy()
    plot_df = plot_df.sort_values("pmt_id")

    fig = go.Figure()

    series = _scale_column(plot_df, y_column).dropna()
    center_val = compute_center(series, method=center_method)
    display_y = _scale_column(plot_df, y_column)

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
        marker=dict(color="steelblue", size=8),
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
            marker=dict(color="red", size=10, symbol="x"),
            text=outlier["pmt_id"].astype(str) if show_outlier_labels else None,
            textposition="top center",
            textfont=dict(color="red", size=10),
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
