# AI Log Insights Chatbot POC

Conversational CLI for querying structured security/monitoring logs. Part of the SpecKit-driven POC in `specs/001-ai-log-chatbot/`.

## Quick Start

```bash
cd stockAiApp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

## Example Queries

- `Show recent ERROR logs`
- `Summarize user activities for ADMIN`
- `Count logs by level`
- `What's the system health?`
- `Show that as a chart`

## SpecKit Artifacts

| Artifact | Path |
|----------|------|
| Specification | `specs/001-ai-log-chatbot/spec.md` |
| Plan | `specs/001-ai-log-chatbot/plan.md` |
| Tasks | `specs/001-ai-log-chatbot/tasks.md` |
| Quickstart | `specs/001-ai-log-chatbot/quickstart.md` |

## Project Structure

```text
stockAiApp/
├── data/sample_logs.csv
├── src/           # Chatbot modules
├── output/        # Generated charts
└── specs/         # SpecKit documentation
```