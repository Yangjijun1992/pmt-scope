from typing import List
"""PMTscope 工具函数模块 — 统计计算与离群点检测"""

import numpy as np
import pandas as pd
from typing import Literal


def compute_center(series: pd.Series, method: Literal["median", "mean"] = "median") -> float:
    """计算中心值（中位数或均值）。"""
    if method == "median":
        return series.median()
    elif method == "mean":
        return series.mean()
    else:
        raise ValueError(f"不支持的中心值方法: {method}")


def detect_outliers_sigma(series: pd.Series, multiplier: float = 3.0) -> pd.Series:
    """使用 3σ 规则检测离群点，返回布尔 Series。"""
    mean = series.mean()
    std = series.std()
    lower = mean - multiplier * std
    upper = mean + multiplier * std
    return (series < lower) | (series > upper)


def detect_outliers_iqr(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """使用 IQR 规则检测离群点，返回布尔 Series。"""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (series < lower) | (series > upper)


def detect_outliers(
    series: pd.Series,
    method: Literal["sigma", "iqr"] = "iqr",
    multiplier: float = 1.5,
) -> pd.Series:
    """检测离群点，返回布尔 Series。"""
    if method == "sigma":
        return detect_outliers_sigma(series, multiplier)
    elif method == "iqr":
        return detect_outliers_iqr(series, multiplier)
    else:
        raise ValueError(f"不支持的离群点检测方法: {method}")


def detect_outliers_df(
    df: pd.DataFrame,
    columns: List[str],
    method: Literal["sigma", "iqr"] = "iqr",
    multiplier: float = 1.5,
) -> pd.DataFrame:
    """对 DataFrame 的多个列进行离群点检测，添加 `_outlier` 标记列。"""
    result = df.copy()
    for col in columns:
        if col in result.columns:
            mask = detect_outliers(result[col], method=method, multiplier=multiplier)
            result[f"{col}_outlier"] = mask
    return result
