"""PMTscope 数据加载与过滤模块"""

import os
import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd
import yaml


REQUIRED_COLUMNS = [
    "id", "pmt_id", "board_id", "channel_id", "measurement_time",
    "run_id", "run_type", "run_tag", "hv", "temperature",
    "spe_gain", "dark_count_rate", "after_pulse_probability", "notes",
]

NUMERIC_COLUMNS = [
    "hv", "temperature", "spe_gain", "dark_count_rate", "after_pulse_probability",
]


def load_config(config_path: str = "config.yaml") -> dict:
    """加载 YAML 配置文件。"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data(config: dict) -> pd.DataFrame:
    """根据配置从 SQLite 或 CSV 加载数据，返回 DataFrame。"""
    db_cfg = config.get("database", {})
    db_type = db_cfg.get("type", "csv")
    db_path = db_cfg.get("path", "data/pmt_data.csv")

    if db_type == "sqlite":
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM pmt_data", conn)
        conn.close()
    elif db_type == "csv":
        df = pd.read_csv(db_path)
    else:
        raise ValueError(f"不支持的数据源类型: {db_type}")

    return _clean_data(df)


def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗数据：类型转换、缺失值处理、时间解析。"""
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "measurement_time" in df.columns:
        df["measurement_time"] = pd.to_datetime(df["measurement_time"], errors="coerce")

    if "notes" in df.columns:
        df["notes"] = df["notes"].fillna("")

    if "id" not in df.columns:
        df["id"] = range(len(df))

    return df


def filter_data(
    df: pd.DataFrame,
    hv_range: Optional[tuple[float, float]] = None,
    run_ids: Optional[list[str]] = None,
    pmt_ids: Optional[list[str]] = None,
    run_types: Optional[list[str]] = None,
    run_tags: Optional[list[str]] = None,
    time_range: Optional[tuple[datetime, datetime]] = None,
) -> pd.DataFrame:
    """按指定条件过滤 DataFrame。"""
    result = df.copy()
    mask = pd.Series(True, index=result.index)

    if hv_range is not None and "hv" in result.columns:
        mask &= (result["hv"] >= hv_range[0]) & (result["hv"] <= hv_range[1])

    if run_ids and "run_id" in result.columns:
        mask &= result["run_id"].isin(run_ids)

    if pmt_ids and "pmt_id" in result.columns:
        mask &= result["pmt_id"].isin(pmt_ids)

    if run_types and "run_type" in result.columns:
        mask &= result["run_type"].isin(run_types)

    if run_tags and "run_tag" in result.columns:
        mask &= result["run_tag"].isin(run_tags)

    if time_range is not None and "measurement_time" in result.columns:
        mask &= (result["measurement_time"] >= time_range[0]) & (result["measurement_time"] <= time_range[1])

    return result[mask].reset_index(drop=True)


def query_records(
    df: pd.DataFrame,
    pmt_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> pd.DataFrame:
    """按 pmt_id 和/或 run_id 查询记录，返回完整记录子集。"""
    result = df.copy()
    mask = pd.Series(True, index=result.index)

    if pmt_id and "pmt_id" in result.columns:
        mask &= result["pmt_id"].astype(str) == str(pmt_id).strip()

    if run_id and "run_id" in result.columns:
        mask &= result["run_id"].astype(str) == str(run_id).strip()

    return result[mask].reset_index(drop=True)


def parse_query_string(query_str: str) -> dict[str, Optional[str]]:
    """解析查询字符串，支持逗号分隔的 pmt_id 和 run_id 组合。"""
    parts = [p.strip() for p in query_str.split(",") if p.strip()]
    result: dict[str, Optional[str]] = {"pmt_id": None, "run_id": None}
    for part in parts:
        if "=" in part:
            key, val = part.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if key in ("pmt_id", "pmtid", "pmt"):
                result["pmt_id"] = val
            elif key in ("run_id", "runid", "run"):
                result["run_id"] = val
        else:
            if result["run_id"] is None:
                result["run_id"] = part
    return result
