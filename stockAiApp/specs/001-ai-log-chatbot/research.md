# Research: AI Log Insights Chatbot

**Date**: 2026-07-14

## Decision 1: Natural Language Parsing Approach

**Decision**: Rule-based keyword and regex intent matching for POC.

**Rationale**: POC.txt explicitly states no external LLM is needed for the basic version. Rule-based parsing is deterministic, offline, fast to demo, and sufficient for structured filter/aggregation patterns (log levels, components, dates, user IDs).

**Alternatives considered**:
- Local LLM (Ollama): Better semantic understanding but adds setup complexity and non-determinism for a POC demo.
- Text-to-SQL: Overkill for in-memory pandas queries; harder to validate on small datasets.
- Azure OpenAI: Out of POC scope; requires API keys and network.

## Decision 2: Data Storage Layer

**Decision**: pandas DataFrame loaded from CSV; no SQLite in initial POC.

**Rationale**: POC.txt describes CSV → pandas as the Cosmos DB simulation. For the sample dataset size, in-memory pandas is simplest and meets all query/aggregation needs.

**Alternatives considered**:
- SQLite persistence: Useful for larger datasets; deferred to keep POC minimal.
- Azure Cosmos DB emulator: Production path per POC.txt; out of scope for local POC.
- JSON files: Less ergonomic for tabular filter/aggregate operations.

## Decision 3: Visualization Library

**Decision**: matplotlib with non-interactive (Agg) backend.

**Rationale**: POC.txt references matplotlib for charts. Agg backend works headless in CLI environments and saves PNG files to `output/`.

**Alternatives considered**:
- plotly: Richer interactivity but requires browser for full value.
- Terminal ASCII charts: Limited for demo presentations.

## Decision 4: Session Context Model

**Decision**: In-memory session holding last QueryIntent, last DataFrame result, and last aggregation series.

**Rationale**: Supports follow-up filters and "show as chart" without a database. Sufficient for single-user CLI demo.

**Alternatives considered**:
- Full conversation LLM memory: Unnecessary without LLM integration.
- Disk-persisted sessions: Out of scope for POC.

## Decision 5: Health / Stock Metaphor Mapping

**Decision**: Map ERROR rate and WARN counts to "system health index" language in response templates.

**Rationale**: POC.txt adapts stock monitoring to log analysis. Template-based health summaries (e.g., "Index health: DEGRADED — 40% ERROR rate in CASB") deliver the metaphor without real market APIs.

**Alternatives considered**:
- Real stock API integration (Alpha Vantage): Explicitly listed as future extension in POC.txt.