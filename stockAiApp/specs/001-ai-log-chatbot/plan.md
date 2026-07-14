# Implementation Plan: AI Log Insights Chatbot

**Branch**: `001-ai-log-chatbot` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ai-log-chatbot/spec.md`

## Summary

Build a Python CLI chatbot that loads structured security/monitoring logs from CSV into an in-memory data store (pandas, with optional SQLite persistence), parses natural language questions via rule-based intent matching, and returns conversational summaries with tables, aggregations, and optional matplotlib charts. The POC simulates Cosmos DB-style retrieval and frames monitoring metrics as "system health" indices, validating the RAG-over-structured-data pattern described in POC.txt.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: pandas, matplotlib, python-dateutil

**Storage**: CSV input file; in-memory pandas DataFrame (SQLite optional for persistence layer)

**Testing**: Manual quickstart validation; pytest optional for unit tests on intent parser

**Target Platform**: Windows/macOS/Linux CLI (local development)

**Project Type**: CLI application (single project)

**Performance Goals**: Sub-second query response on sample dataset (<5k rows)

**Constraints**: No external LLM API required; rule-based NL parsing only; offline-capable

**Scale/Scope**: Single analyst, single dataset, demo/POC scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Project constitution ratified | PASS (waived) | `.specify/memory/constitution.md` is template-only; POC follows simplicity and CLI-first defaults from POC.txt |
| Library-first modules | PASS | Separate modules for data loading, intent parsing, query engine, response formatting, visualization |
| CLI interface | PASS | Primary interface is interactive CLI with text in/out |
| Test-first | PASS (relaxed) | Manual quickstart validation required; automated tests optional for POC |
| Simplicity / YAGNI | PASS | Rule-based parsing, no LLM, no Cosmos DB emulator in v1 |

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-log-chatbot/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.md
├── tasks.md             # Phase 2 output
└── spec.md
```

### Source Code (repository root)

```text
stockAiApp/
├── data/
│   └── sample_logs.csv
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── data_loader.py       # CSV → DataFrame
│   ├── intent_parser.py     # NL → QueryIntent
│   ├── query_engine.py      # Filter/aggregate execution
│   ├── response_builder.py  # Summary + table formatting
│   ├── session.py           # Follow-up context
│   └── visualizer.py        # Chart generation
├── output/                  # Generated charts (gitignored)
├── requirements.txt
├── .gitignore
└── README.md
```

**Structure Decision**: Single Python CLI project under `stockAiApp/` with modular `src/` packages. Sample data in `data/`. Charts written to `output/`.

## Complexity Tracking

No constitution violations requiring justification.