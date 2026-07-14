from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .session import QueryIntent, QueryResult


def execute_intent(
    df: pd.DataFrame,
    intent: QueryIntent,
    max_rows: int = 20,
    base_df: pd.DataFrame | None = None,
) -> QueryResult:
    if intent.intent_type == "aggregate":
        return _run_aggregation(df, intent, max_rows)
    if intent.intent_type == "health_summary":
        return _run_health_summary(df, max_rows)
    if intent.intent_type == "follow_up" and base_df is not None:
        filtered = _apply_filters(base_df, intent.filters)
        return _build_filter_result(filtered, intent, max_rows, source_df=df)
    filtered = _apply_filters(df, intent.filters)
    return _build_filter_result(filtered, intent, max_rows, source_df=df)


def _apply_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    result = df.copy()

    if "log_level" in filters:
        result = result[result["log_level"] == filters["log_level"].upper()]

    if "component" in filters:
        target = filters["component"]
        result = result[result["component"].str.upper() == str(target).upper()]

    if "system_name" in filters:
        result = result[result["system_name"].str.contains(filters["system_name"], case=False, na=False)]

    if "user_id" in filters:
        result = result[result["user_ID"].str.upper() == filters["user_id"].upper()]

    if "keyword" in filters:
        result = result[result["message"].str.contains(filters["keyword"], case=False, na=False)]

    if "since" in filters:
        since: datetime = filters["since"]
        if since.tzinfo is None:
            since = since.replace(tzinfo=pd.Timestamp.now(tz="UTC").tzinfo)
        result = result[result["Timestamp"] >= pd.Timestamp(since)]

    if filters.get("recent"):
        result = result.sort_values("Timestamp", ascending=False)

    return result.sort_values("Timestamp", ascending=False).reset_index(drop=True)


def _build_filter_result(
    filtered: pd.DataFrame,
    intent: QueryIntent,
    max_rows: int,
    source_df: pd.DataFrame | None = None,
) -> QueryResult:
    total = len(filtered)
    truncated = total > max_rows
    display = filtered.head(max_rows)
    parts = []
    if intent.filters.get("log_level"):
        parts.append(f"{intent.filters['log_level']} logs")
    if intent.filters.get("component"):
        parts.append(f"component {intent.filters['component']}")
    if intent.filters.get("system_name"):
        parts.append(f"system {intent.filters['system_name']}")
    if intent.filters.get("user_id"):
        parts.append(f"user {intent.filters['user_id']}")
    if intent.filters.get("keyword"):
        parts.append(f"messages containing '{intent.filters['keyword']}'")

    subject = ", ".join(parts) if parts else "matching logs"
    if total == 0:
        summary = _build_empty_summary(intent, source_df)
    elif intent.filters.get("user_id"):
        summary = _build_user_activity_summary(filtered, intent.filters["user_id"])
    else:
        summary = f"Found {total} {subject}."

    return QueryResult(
        rows=display,
        total_count=total,
        summary=summary,
        truncated=truncated,
        full_rows=filtered,
    )


def _run_aggregation(df: pd.DataFrame, intent: QueryIntent, max_rows: int) -> QueryResult:
    working = _apply_filters(df, intent.filters)

    if intent.aggregate_by == "log_level":
        agg = working.groupby("log_level", as_index=False).size().rename(columns={"size": "count"})
        agg = agg.sort_values("count", ascending=False)
        summary = "Log counts by level: " + ", ".join(f"{r.log_level}={int(r.count)}" for r in agg.itertuples())
    elif intent.aggregate_by == "component":
        agg = working.groupby("component", as_index=False).size().rename(columns={"size": "count"})
        agg = agg.sort_values("count", ascending=False)
        summary = "Log counts by component: " + ", ".join(f"{r.component}={int(r.count)}" for r in agg.itertuples())
    elif intent.aggregate_by == "time_bucket":
        bucket = intent.time_bucket or "day"
        temp = working.copy()
        if bucket == "day":
            temp["bucket"] = temp["Timestamp"].dt.floor("D")
        else:
            temp["bucket"] = temp["Timestamp"].dt.floor("h")
        agg = temp.groupby("bucket", as_index=False).size().rename(columns={"size": "count"})
        agg = agg.sort_values("bucket")
        trend_note = _describe_trend(agg["count"].tolist())
        summary = (
            f"Trend over time ({bucket} buckets): {int(agg['count'].sum())} events tracked. {trend_note}"
        )
    else:
        agg = pd.DataFrame()
        summary = "No aggregation type recognized."

    display = agg.head(max_rows)
    return QueryResult(
        rows=display,
        total_count=len(agg),
        summary=summary,
        aggregation=agg,
        truncated=len(agg) > max_rows,
    )


def _run_health_summary(df: pd.DataFrame, max_rows: int) -> QueryResult:
    total = len(df)
    if total == 0:
        return QueryResult(
            rows=pd.DataFrame(),
            total_count=0,
            summary="No log data available to assess system health.",
        )

    level_counts = df["log_level"].value_counts()
    errors = int(level_counts.get("ERROR", 0))
    warns = int(level_counts.get("WARN", 0))
    error_rate = round((errors / total) * 100, 1)

    if error_rate >= 30:
        status = "CRITICAL"
    elif error_rate >= 15:
        status = "DEGRADED"
    elif warns > errors:
        status = "CAUTION"
    else:
        status = "HEALTHY"

    comp_stats = (
        df.assign(is_error=df["log_level"] == "ERROR")
        .groupby("component")
        .agg(total=("log_level", "count"), errors=("is_error", "sum"))
        .reset_index()
    )
    comp_stats["error_rate"] = (comp_stats["errors"] / comp_stats["total"] * 100).round(1)
    flagged = comp_stats[comp_stats["error_rate"] >= 20]

    summary = (
        f"System health index: {status} - overall ERROR rate is {error_rate}% "
        f"({errors} errors, {warns} warnings across {total} events)."
    )
    if not flagged.empty:
        flags = ", ".join(f"{r.component} ({r.error_rate}%)" for r in flagged.itertuples())
        summary += f" Components needing attention: {flags}."

    display = comp_stats.sort_values("error_rate", ascending=False).head(max_rows)
    return QueryResult(
        rows=display,
        total_count=len(comp_stats),
        summary=summary,
        aggregation=display,
        truncated=len(comp_stats) > max_rows,
    )


def _build_user_activity_summary(filtered: pd.DataFrame, user_id: str) -> str:
    total = len(filtered)
    level_breakdown = filtered["log_level"].value_counts().to_dict()
    parts = [f"{level}={count}" for level, count in sorted(level_breakdown.items())]
    components = ", ".join(sorted(filtered["component"].unique().tolist()))
    return (
        f"Activity summary for {user_id}: {total} events across [{components}]. "
        f"Breakdown by level: {', '.join(parts)}."
    )


def _build_empty_summary(intent: QueryIntent, source_df: pd.DataFrame | None) -> str:
    summary = "No matching logs found."
    hints: list[str] = []

    if source_df is not None and not source_df.empty:
        if intent.filters.get("since"):
            min_ts = source_df["Timestamp"].min()
            max_ts = source_df["Timestamp"].max()
            hints.append(
                f"Dataset spans {min_ts.date()} to {max_ts.date()}; your date filter may be outside this range."
            )
        if intent.filters.get("component"):
            available = ", ".join(sorted(source_df["component"].unique().tolist()))
            hints.append(f"Available components: {available}.")
        if intent.filters.get("user_id"):
            available = ", ".join(sorted(u for u in source_df["user_ID"].unique().tolist() if u))
            hints.append(f"Available users: {available}.")
        if intent.filters.get("system_name"):
            available = ", ".join(sorted(source_df["system_name"].unique().tolist()))
            hints.append(f"Available systems: {available}.")

    hints.append("Try: 'Show ERROR logs' or 'Count by component'.")
    return summary + " " + " ".join(hints)


def _describe_trend(counts: list[int]) -> str:
    if len(counts) < 2:
        return "Insufficient data for trend interpretation."
    if counts[-1] > counts[0]:
        return "Trend interpretation: increasing over the period."
    if counts[-1] < counts[0]:
        return "Trend interpretation: decreasing over the period."
    return "Trend interpretation: stable over the period."