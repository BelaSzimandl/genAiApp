# Feature Specification: Azure Cosmos DB Log Store

**Feature Branch**: `002-cosmos-log-store`

**Created**: 2026-07-15

**Status**: In Progress

**Input**: Continue POC from POC.txt — store and load structured monitoring logs in Azure Cosmos DB (cloud), replacing pure CSV-only storage for production-path validation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cloud Log Persistence (Priority: P1)

An operator provisions Azure Cosmos DB and ingests the sample log CSV into a NoSQL container so log data lives in the cloud, not only on disk.

**Why this priority**: POC.txt production path is Cosmos DB; local CSV alone does not prove cloud readiness.

**Independent Test**: Run ingest CLI against a provisioned account; verify document count in portal or via query equals CSV row count.

**Acceptance Scenarios**:

1. **Given** Cosmos endpoint and key are configured, **When** the operator runs ingest on `sample_logs.csv`, **Then** all valid rows are upserted into the `log_entries` container.
2. **Given** documents already exist, **When** ingest is re-run, **Then** items are upserted without duplicate-key failures (idempotent by `id`/`corr_id`).

### User Story 2 - Chatbot Reads from Cosmos (Priority: P1)

An analyst starts the chatbot with a Cosmos data source and asks the same natural-language questions as before; results match CSV-backed behavior for the sample dataset.

**Why this priority**: End-to-end demo of RAG-style structured retrieval over cloud storage.

**Independent Test**: Ingest sample data; run chatbot with `--source cosmos`; execute quickstart filter/aggregation queries.

**Acceptance Scenarios**:

1. **Given** logs are in Cosmos, **When** the user asks "Show recent ERROR logs", **Then** results match ERROR rows from the cloud dataset.
2. **Given** Cosmos is empty or unreachable, **When** the chatbot starts with `--source cosmos`, **Then** a clear error explains how to configure keys or run ingest.

### User Story 3 - Secure Local Configuration (Priority: P2)

Developers store connection settings in environment variables / local `.env` without committing secrets to git.

**Acceptance Scenarios**:

1. **Given** `.env` is gitignored, **When** a developer clones the repo, **Then** `.env.example` documents required variables without real keys.

### User Story 4 - Semantic Vector Search on Messages (Priority: P1)

An analyst asks meaning-based questions such as "Find logs about connection problems" without exact keywords. The system embeds the query and ranks Cosmos log documents by vector similarity on the message field.

**Why this priority**: POC.txt production path includes embeddings and vector search for unstructured message text.

**Independent Test**: Ingest sample logs with embeddings; run three semantic queries; verify top hit is relevant for each.

**Acceptance Scenarios**:

1. **Given** documents with embeddings in Cosmos, **When** the user asks about connection problems, **Then** top results include CASB connection timeout messages.
2. **Given** embeddings are present, **When** native vector index is not yet available, **Then** search still ranks correctly via cosine over stored embeddings.
3. **Given** native vector policy is enabled later, **When** `COSMOS_VECTOR_NATIVE=1`, **Then** search may use Cosmos `VectorDistance`.

## Requirements *(mandatory)*

- **FR-001**: System MUST support Azure Cosmos DB for NoSQL as the cloud store for log entries.
- **FR-002**: System MUST map log fields: Timestamp, system_name, component, log_level, corr_id, user_ID, message.
- **FR-003**: System MUST use partition key `/component` for the log container.
- **FR-004**: System MUST provide a CLI to ingest CSV into Cosmos.
- **FR-005**: System MUST load logs from Cosmos into the existing chatbot query pipeline.
- **FR-006**: Secrets MUST NOT be committed to source control.
- **FR-007**: System MUST generate and store vector embeddings for each log message on ingest.
- **FR-008**: System MUST support natural-language semantic queries that rank logs by embedding similarity.

## Success Criteria

- **SC-001**: Cosmos account, database `LogInsights`, and container `log_entries` exist in Azure.
- **SC-002**: Sample CSV can be fully ingested in under 2 minutes for the POC dataset.
- **SC-003**: Chatbot with `--source cosmos` supports the same query classes as CSV mode for sample data.
- **SC-004**: Semantic queries return relevant top hits for timeout, vulnerability, and suspicious-download scenarios on the sample set.

