from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "Timestamp",
    "system_name",
    "component",
    "log_level",
    "corr_id",
    "user_ID",
    "message",
]

VALID_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}


def load_logs(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Could not load log data from {file_path}. Check file exists.")

    df = pd.read_csv(file_path)
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

    df = df.dropna(how="all")
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp", "system_name", "component", "log_level", "message"])

    df["log_level"] = df["log_level"].astype(str).str.upper().str.strip()
    invalid = ~df["log_level"].isin(VALID_LEVELS)
    if invalid.any():
        df = df[~invalid]

    df["component"] = df["component"].astype(str).str.strip()
    df["system_name"] = df["system_name"].astype(str).str.strip()
    df["user_ID"] = df["user_ID"].fillna("").astype(str).str.strip()
    df["message"] = df["message"].astype(str).str.strip()

    return df.sort_values("Timestamp", ascending=False).reset_index(drop=True)