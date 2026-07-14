# Quickstart: AI Log Insights Chatbot

**Date**: 2026-07-14

## Prerequisites

- Python 3.11 or later
- pip

## Setup

```bash
cd stockAiApp
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
python -m src.main
```

Optional custom data path:

```bash
python -m src.main --data data/sample_logs.csv
```

## Validation Scenarios

### Scenario 1: Filter by log level (User Story 1)

1. Start the chatbot.
2. Ask: `Show recent ERROR logs`
3. **Expected**: Summary states ERROR count; table shows only ERROR rows sorted by timestamp descending.

### Scenario 2: Filter by user (User Story 1)

1. Ask: `Summarize user activities for ADMIN`
2. **Expected**: Summary of ADMIN activity; table filtered to user_ID=ADMIN.

### Scenario 3: Aggregation (User Story 2)

1. Ask: `Count logs by level`
2. **Expected**: Counts per log_level printed in summary and table.

### Scenario 4: Health summary (User Story 2)

1. Ask: `What's the system health?`
2. **Expected**: Health-style summary with overall status and component flags.

### Scenario 5: Chart generation (User Story 3)

1. Ask: `Count by component`
2. Then ask: `Show that as a chart`
3. **Expected**: PNG saved under `output/` with confirmation message.

### Scenario 6: Follow-up (User Story 3)

1. Ask: `Show CASB logs`
2. Then ask: `only WARN level`
3. **Expected**: Results refined to CASB + WARN from prior context.

### Scenario 7: Help and unknown query

1. Type: `help`
2. **Expected**: List of example queries.
3. Type: `hello there`
4. **Expected**: Guidance message, not a crash.

## Troubleshooting

- **ModuleNotFoundError**: Ensure virtual environment is activated and dependencies installed.
- **File not found**: Verify `data/sample_logs.csv` exists or pass `--data` with correct path.
- **Empty charts**: Run an aggregation query before requesting a chart.