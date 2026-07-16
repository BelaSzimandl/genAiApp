"""Log query tools backed by Azure Cosmos DB (preferred) or bundled sample CSV."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

REQUIRED = [
    "Timestamp",
    "system_name",
    "component",
    "log_level",
    "corr_id",
    "user_ID",
    "message",
]


def _csv_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "sample_logs.csv"


@lru_cache(maxsize=1)
def _load_df() -> pd.DataFrame:
    source = os.getenv("LOG_DATA_SOURCE", "auto").strip().lower()
    if source in {"cosmos", "auto"}:
        try:
            return _load_cosmos()
        except Exception:
            if source == "cosmos":
                raise
    return _load_csv()


def _load_csv() -> pd.DataFrame:
    path = _csv_path()
    if not path.exists():
        raise FileNotFoundError(f"Sample log CSV not found at {path}")
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df["log_level"] = df["log_level"].astype(str).str.upper()
    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp", ascending=False)


def _load_cosmos() -> pd.DataFrame:
    from azure.cosmos import CosmosClient
    from dotenv import load_dotenv

    load_dotenv()
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database = os.getenv("COSMOS_DATABASE", "LogInsights").strip()
    container = os.getenv("COSMOS_CONTAINER", "log_entries").strip()
    if not endpoint or not key:
        raise ValueError("COSMOS_ENDPOINT and COSMOS_KEY required for Cosmos source")

    client = CosmosClient(endpoint, credential=key)
    cont = client.get_database_client(database).get_container_client(container)
    items = list(
        cont.query_items(
            query=(
                "SELECT c.Timestamp, c.system_name, c.component, c.log_level, "
                "c.corr_id, c.user_ID, c.message FROM c"
            ),
            enable_cross_partition_query=True,
        )
    )
    if not items:
        return pd.DataFrame(columns=REQUIRED)
    df = pd.DataFrame(items)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df["log_level"] = df["log_level"].astype(str).str.upper()
    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp", ascending=False)


def _format_rows(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "No matching log entries."
    show = df.head(max_rows)
    lines = [f"Showing {len(show)} of {len(df)} matching rows:"]
    for _, row in show.iterrows():
        ts = row["Timestamp"]
        ts_s = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        lines.append(
            f"- [{ts_s}] {row['log_level']} {row['component']} "
            f"user={row.get('user_ID','')} | {row['message']}"
        )
    if len(df) > max_rows:
        lines.append(f"... truncated; total matches: {len(df)}")
    return "\n".join(lines)


def filter_logs(
    log_level: str | None = None,
    component: str | None = None,
    user_id: str | None = None,
    keyword: str | None = None,
    max_rows: int = 10,
) -> str:
    df = _load_df().copy()
    if log_level:
        df = df[df["log_level"] == log_level.upper()]
    if component:
        df = df[df["component"].str.upper() == component.upper()]
    if user_id:
        df = df[df["user_ID"].str.upper() == user_id.upper()]
    if keyword:
        df = df[df["message"].str.contains(keyword, case=False, na=False)]
    return _format_rows(df, max_rows=max_rows)


def count_logs(group_by: str = "log_level") -> str:
    df = _load_df()
    key = (group_by or "log_level").lower()
    if key in {"level", "log_level"}:
        counts = df["log_level"].value_counts()
        title = "Counts by log_level"
    elif key in {"component", "components"}:
        counts = df["component"].value_counts()
        title = "Counts by component"
    elif key in {"time", "day", "date"}:
        days = df["Timestamp"].dt.floor("D")
        counts = days.value_counts().sort_index()
        title = "Counts by day"
    else:
        return f"Unknown group_by '{group_by}'. Use log_level, component, or time."
    lines = [title + ":"]
    for name, val in counts.items():
        lines.append(f"- {name}: {int(val)}")
    lines.append(f"Total rows: {len(df)}")
    return "\n".join(lines)


def health_summary() -> str:
    df = _load_df()
    total = len(df)
    if total == 0:
        return "No logs available — system health unknown."
    errors = int((df["log_level"] == "ERROR").sum())
    warns = int((df["log_level"] == "WARN").sum())
    error_rate = errors / total
    if error_rate >= 0.3:
        status = "DEGRADED"
    elif error_rate >= 0.1 or warns / total >= 0.3:
        status = "WATCH"
    else:
        status = "HEALTHY"
    by_comp = (
        df[df["log_level"].isin(["ERROR", "WARN"])]
        .groupby("component")
        .size()
        .sort_values(ascending=False)
    )
    lines = [
        f"System health index: {status}",
        f"ERROR rate: {error_rate:.0%} ({errors}/{total})",
        f"WARN count: {warns}",
        "Hotspots (ERROR+WARN by component):",
    ]
    if by_comp.empty:
        lines.append("- none")
    else:
        for comp, n in by_comp.items():
            lines.append(f"- {comp}: {int(n)}")
    return "\n".join(lines)


def semantic_search_logs(query: str, top_k: int = 5) -> str:
    """Keyword-boosted ranking as a lightweight semantic proxy (no model download in host)."""
    df = _load_df().copy()
    if df.empty:
        return "No logs available."
    q = (query or "").lower()
    tokens = [t for t in q.replace("?", " ").split() if len(t) > 2]
    if not tokens:
        return _format_rows(df, max_rows=top_k)

    def score(msg: str) -> float:
        m = str(msg).lower()
        return float(sum(1 for t in tokens if t in m))

    df = df.copy()
    df["_score"] = df["message"].map(score)
    ranked = df[df["_score"] > 0].sort_values(["_score", "Timestamp"], ascending=[False, False])
    if ranked.empty:
        # Fall back to keyword substring of full query
        ranked = df[df["message"].str.contains("|".join(tokens), case=False, na=False, regex=True)]
    if ranked.empty:
        return f"No logs matched semantic query '{query}'."
    return _format_rows(ranked.drop(columns=["_score"], errors="ignore"), max_rows=top_k)
