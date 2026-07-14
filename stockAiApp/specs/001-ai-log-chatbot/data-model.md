# Data Model: AI Log Insights Chatbot

**Date**: 2026-07-14

## Entities

### LogEntry

Represents one row of monitoring/security log data.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Timestamp | datetime (ISO 8601) | Yes | Event occurrence time |
| system_name | string | Yes | Originating system host or service identifier |
| component | string | Yes | Subsystem or product area (e.g., CASB, PAM, VulnScanner) |
| log_level | enum string | Yes | Severity: DEBUG, INFO, WARN, ERROR, CRITICAL |
| corr_id | string | No | Correlation ID for tracing related events |
| user_ID | string | No | Associated user or service account |
| message | string | Yes | Free-text log message body |

**Validation rules**:
- `log_level` must be one of: DEBUG, INFO, WARN, ERROR, CRITICAL (case-insensitive input normalized to uppercase).
- `Timestamp` must parse as valid ISO 8601 datetime.
- Empty CSV rows are skipped; missing required fields log a warning and skip row.

### QueryIntent

Parsed representation of a user's natural language request.

| Field | Type | Description |
|-------|------|-------------|
| intent_type | enum | `filter`, `aggregate`, `health_summary`, `visualize`, `follow_up`, `help`, `unknown` |
| filters | dict | Optional keys: `log_level`, `component`, `system_name`, `user_id`, `keyword`, `since`, `until` |
| aggregate_by | string | Optional: `log_level`, `component`, `time_bucket` |
| time_bucket | string | Optional: `hour`, `day` (used when aggregate_by is `time_bucket`) |
| refine_previous | bool | True when follow-up should apply to prior result set |
| chart_type | string | Optional: `bar`, `line` (for visualize intent) |

### QueryResult

Output of executing a QueryIntent against the dataset.

| Field | Type | Description |
|-------|------|-------------|
| rows | DataFrame | Matching log entries (may be truncated) |
| total_count | int | Full match count before truncation |
| aggregation | Series/DataFrame | Present for aggregate intents |
| summary | string | Conversational summary text |
| truncated | bool | True if rows exceed display limit |

### SessionContext

In-memory state for follow-up questions.

| Field | Type | Description |
|-------|------|-------------|
| last_intent | QueryIntent | Most recent parsed intent |
| last_result | QueryResult | Most recent query result |
| last_aggregation | object | Aggregation data for chart requests |
| history | list[string] | Recent user queries (max 10) |

## Relationships

- One **LogEntry** dataset (CSV) is loaded into a single DataFrame at startup.
- Each user question produces one **QueryIntent** parsed from text.
- **QueryIntent** executes against the full dataset or **SessionContext.last_result** (follow-up).
- **QueryResult** may feed **SessionContext** and **visualizer** for chart output.

## Display Limits

- Maximum rows shown in table output: 20
- Maximum session history entries: 10