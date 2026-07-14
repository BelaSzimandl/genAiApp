from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

from .session import QueryIntent

LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")
KNOWN_COMPONENTS = ("CASB", "PAM", "VULNSCANNER", "VULN SCANNER")


def parse_intent(text: str, available_components: list[str] | None = None) -> QueryIntent:
    normalized = text.strip()
    lower = normalized.lower()

    if not normalized:
        return QueryIntent(intent_type="unknown")

    if lower in {"help", "?"}:
        return QueryIntent(intent_type="help")

    if _is_chart_request(lower):
        chart_type = "line" if "line" in lower else "bar"
        return QueryIntent(intent_type="visualize", chart_type=chart_type)

    if _is_health_query(lower):
        return QueryIntent(intent_type="health_summary")

    if _is_follow_up(lower):
        intent = QueryIntent(intent_type="follow_up", refine_previous=True)
        intent.filters = _extract_filters(lower, available_components)
        return intent

    aggregate_by = _detect_aggregation(lower)
    if aggregate_by:
        intent = QueryIntent(intent_type="aggregate", aggregate_by=aggregate_by)
        intent.filters = _extract_filters(lower, available_components)
        if "trend" in lower or "over time" in lower:
            intent.time_bucket = "day"
            intent.filters.setdefault("log_level", "ERROR")
        return intent

    intent = QueryIntent(intent_type="filter")
    intent.filters = _extract_filters(lower, available_components)
    if intent.filters:
        return intent

    return QueryIntent(intent_type="unknown")


def _is_chart_request(lower: str) -> bool:
    return "chart" in lower or "graph" in lower or "plot" in lower


def _is_health_query(lower: str) -> bool:
    return "system health" in lower or "health index" in lower or "index health" in lower


def _is_follow_up(lower: str) -> bool:
    starters = ("only ", "just ", "filter ", "narrow ", "limit ")
    return lower.startswith(starters) or "last hour" in lower or "last day" in lower


def _detect_aggregation(lower: str) -> str | None:
    if "count" in lower or "how many" in lower:
        if "component" in lower or "by component" in lower:
            return "component"
        if "level" in lower or "by level" in lower:
            return "log_level"
    if "trend" in lower or "over time" in lower:
        return "time_bucket"
    if "summarize" in lower and "activit" in lower:
        return None
    return None


def _extract_filters(lower: str, available_components: list[str] | None) -> dict:
    filters: dict = {}

    for level in LOG_LEVELS:
        if level.lower() in lower or level.lower() + "s" in lower.split():
            filters["log_level"] = level
            break
    if "warning" in lower or "warnings" in lower:
        filters["log_level"] = "WARN"

    component = _match_component(lower, available_components or [])
    if component:
        filters["component"] = component

    activity_match = re.search(r"activit(?:y|ies)\s+for\s+([a-z0-9_-]+)", lower)
    if activity_match:
        filters["user_id"] = activity_match.group(1).upper()
    elif "for admin" in lower:
        filters["user_id"] = "ADMIN"
    else:
        user_match = re.search(r"(?:for user|user)\s+([a-z0-9_-]+)", lower)
        if user_match and user_match.group(1) not in {"activities", "activity"}:
            filters["user_id"] = user_match.group(1).upper()

    if "casb" in lower and "component" not in filters:
        filters["component"] = "CASB"
    if "pam" in lower and "component" not in filters:
        filters["component"] = "PAM"
    if ("vuln" in lower or "scanner" in lower) and "component" not in filters:
        filters["component"] = "VulnScanner"

    system_match = re.search(
        r"(?:system|host)\s+([a-z0-9][a-z0-9._-]+)",
        lower,
    )
    if system_match:
        filters["system_name"] = system_match.group(1)

    keyword_match = re.search(r"(?:containing|with|about|mentioning)\s+['\"]?(\w+)", lower)
    if keyword_match:
        filters["keyword"] = keyword_match.group(1)
    elif "timeout" in lower:
        filters["keyword"] = "timeout"
    elif "threat" in lower:
        filters["keyword"] = "threat"

    since = _parse_date_filter(lower)
    if since:
        filters["since"] = since

    if "recent" in lower and "since" not in filters:
        filters["recent"] = True

    if "last hour" in lower:
        filters["since"] = datetime.now(timezone.utc) - timedelta(hours=1)
    elif "last day" in lower or "today" in lower:
        filters["since"] = datetime.now(timezone.utc) - timedelta(days=1)

    return filters


def _match_component(lower: str, available: list[str]) -> str | None:
    for comp in available:
        if comp.lower() in lower:
            return comp
    return None


def _parse_date_filter(lower: str) -> datetime | None:
    patterns = [
        r"after\s+([a-z]+\s+\d{1,2}(?:,?\s+\d{4})?)",
        r"since\s+([a-z]+\s+\d{1,2}(?:,?\s+\d{4})?)",
        r"from\s+([a-z]+\s+\d{1,2}(?:,?\s+\d{4})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            try:
                parsed = date_parser.parse(match.group(1), default=datetime(2025, 1, 1))
                return parsed.replace(tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                return None
    return None