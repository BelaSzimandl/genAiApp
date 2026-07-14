from __future__ import annotations

import pandas as pd

from .session import QueryResult


def format_response(result: QueryResult) -> str:
    lines = [result.summary, ""]

    if result.rows is not None and not result.rows.empty:
        shown = len(result.rows)
        total = result.total_count
        if result.truncated:
            lines.append(f"Results (showing {shown} of {total}):")
        else:
            lines.append(f"Results ({total} rows):")
        lines.append(_format_table(result.rows))
    elif result.total_count == 0:
        lines.append("No rows to display.")

    return "\n".join(lines)


def format_unknown() -> str:
    return (
        "I didn't understand that. Type 'help' for examples.\n"
        "Try: 'Show recent ERROR logs', 'Count logs by level', or 'What's the system health?'"
    )


def format_help() -> str:
    return """AI Log Insights Chatbot — Example queries:

  Filter:
    • Show recent ERROR logs
    • CASB warnings
    • Summarize user activities for ADMIN
    • Errors after May 1
    • Logs containing timeout

  Aggregate:
    • Count logs by level
    • Count by component
    • Error trend over time
    • What's the system health?

  Follow-up / Charts:
    • only WARN level
    • Show that as a chart

  Commands: help, quit, exit
"""


def format_chart_message(path: str) -> str:
    return f"Chart saved to: {path}"


def format_no_chart_context() -> str:
    return "Run a query or aggregation first, then ask for a chart."


def _format_table(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    widths = {col: max(len(col), *(len(str(v)) for v in df[col].head(20))) for col in columns}

    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    rows = []
    for _, row in df.iterrows():
        rows.append(" | ".join(str(row[col]).ljust(widths[col]) for col in columns))

    return "\n".join([header, separator, *rows])