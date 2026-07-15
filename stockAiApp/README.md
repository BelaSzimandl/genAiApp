# AI Log Insights Chatbot POC

Conversational CLI for querying structured security/monitoring logs. SpecKit features: `001-ai-log-chatbot`, `002-cosmos-log-store`.

## Quick Start (CSV)

```bash
cd stockAiApp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

## Azure Cosmos DB

Cloud store for logs (feature `002-cosmos-log-store`).

| Item | Value |
|------|--------|
| Subscription | Visual Studio Professional |
| Resource group | `rg-stockai-poc` |
| Account | `cosmos-stockai-poc-ne2` |
| Region | Sweden Central |
| Database | `LogInsights` |
| Container | `log_entries` (partition key `/component`) |
| Portal | [Cosmos accounts](https://portal.azure.com/#browse/Microsoft.DocumentDb%2FdatabaseAccounts) |

### Configure secrets

```bash
copy .env.example .env
# Set COSMOS_KEY from Portal → Keys, or:
# az cosmosdb keys list -n cosmos-stockai-poc-ne2 -g rg-stockai-poc --type keys
```

### Ingest sample data and chat from Cosmos

```bash
python -m src.ingest_cosmos
python -m src.main --source cosmos
```

### Vector / semantic search

Each log document stores a 384-d `embedding` on the `message` field (fastembed `BAAI/bge-small-en-v1.5`).

| Mode | How |
|------|-----|
| **Default (working now)** | Embeddings stored in Cosmos; ranked with local cosine over those vectors |
| **Native Cosmos vector index** | Account capability `EnableNoSQLVectorSearch` is set; create vector policy via `infra/enable-vector-container.ps1` when Azure finishes enabling (can take ~15+ min), then set `COSMOS_VECTOR_NATIVE=1` |

Semantic example queries:

```text
Find logs about connection problems
Search for failed scans
Related to password rotation
Suspicious activity
Any threats
```

```bash
python -m src.main --source cosmos
# You> Find logs about connection problems
```

Promote to native vector index (after capability propagates):

```powershell
pwsh ./infra/enable-vector-container.ps1
python -m src.ingest_cosmos
# set COSMOS_VECTOR_NATIVE=1 in .env
```

## Example Queries

- `Show recent ERROR logs`
- `Summarize user activities for ADMIN`
- `Count logs by level`
- `What's the system health?`
- `Show that as a chart`
- `Find logs about connection problems`

## SpecKit Artifacts

| Artifact | Path |
|----------|------|
| Spec 001 | `specs/001-ai-log-chatbot/spec.md` |
| Spec 002 | `specs/002-cosmos-log-store/spec.md` |
| Plan 002 | `specs/002-cosmos-log-store/plan.md` |

## Project Structure

```text
stockAiApp/
├── data/sample_logs.csv
├── infra/         # Cosmos vector policy + enable script
├── src/           # Chatbot + cosmos_store / embeddings / ingest
├── output/        # Generated charts
├── .env.example   # Cosmos + embedding settings
└── specs/         # SpecKit documentation
```
