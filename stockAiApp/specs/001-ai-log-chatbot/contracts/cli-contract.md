# CLI Contract: AI Log Insights Chatbot

**Date**: 2026-07-14

## Entry Point

```bash
python -m src.main [--data PATH] [--max-rows N]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--data` | `data/sample_logs.csv` | Path to log CSV file |
| `--max-rows` | `20` | Maximum rows displayed per query |

## Interactive Commands

| Input | Behavior |
|-------|----------|
| Natural language question | Parse intent, execute query, print summary + table |
| `help` | Print supported query patterns and examples |
| `quit` / `exit` | End session |

## Supported Query Patterns (NL)

### Filter Queries

| Pattern Example | Parsed Filters |
|-----------------|----------------|
| "Show recent ERROR logs" | `log_level=ERROR`, sort desc by timestamp |
| "CASB warnings" | `component=CASB`, `log_level=WARN` |
| "Summarize user activities for ADMIN" | `user_id=ADMIN` |
| "Errors after May 1" | `log_level=ERROR`, `since=2025-05-01` |
| "Logs containing timeout" | `keyword=timeout` |

### Aggregation Queries

| Pattern Example | Aggregation |
|-----------------|-------------|
| "Count logs by level" | group by `log_level` |
| "Count by component" | group by `component` |
| "Error trend over time" | ERROR filter + time_bucket=day |
| "What's the system health?" | health_summary intent |

### Visualization Queries

| Pattern Example | Behavior |
|-----------------|----------|
| "Show that as a chart" | Chart from last aggregation (bar default) |
| "Show as line chart" | Line chart from last aggregation |

### Follow-Up Queries

| Pattern Example | Behavior |
|-----------------|----------|
| "only WARN level" | Refine last result with additional filter |
| "filter to last hour" | Apply time filter to last result |

## Response Format

```
[Summary line — conversational insight]

[Optional health index line for health/aggregate queries]

Results (showing X of Y):
┌──────────┬─────────────┬───────────┬ ...
│ Timestamp│ system_name │ log_level │ ...
└──────────┴─────────────┴───────────┴ ...

[Optional] Chart saved to: output/chart_<timestamp>.png
```

## Error Responses

| Condition | Message |
|-----------|---------|
| Data file missing | `Error: Could not load log data from <path>. Check file exists.` |
| No matches | `No matching logs found. Try: "Show ERROR logs" or "Count by component".` |
| Unknown intent | `I didn't understand that. Type 'help' for examples.` |
| Chart without prior query | `Run a query or aggregation first, then ask for a chart.` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Normal exit (user quit or EOF) |
| 1 | Data load failure at startup |