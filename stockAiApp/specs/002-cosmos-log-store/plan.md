# Implementation Plan: Azure Cosmos DB Log Store

**Branch**: `002-cosmos-log-store` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

## Summary

Provision Azure Cosmos DB (NoSQL) in the user's subscription, create `LogInsights` / `log_entries`, and extend `stockAiApp` with ingest + load modules so the existing CLI chatbot can use cloud-backed data.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: azure-cosmos, python-dotenv (plus existing pandas stack)

**Storage**: Azure Cosmos DB for NoSQL (account `cosmos-stock-market-ai`, Poland Central)

**Azure resources**:
| Resource | Value |
|----------|--------|
| Subscription | Visual Studio Professional |
| Resource group | `stock-market-ai-rg` (same RG as Foundry chatbot; RG metadata Poland Central) |
| Account | `cosmos-stock-market-ai` |
| Account region | Poland Central (West Europe was capacity-blocked) |
| Endpoint | `https://cosmos-stock-market-ai.documents.azure.com:443/` |
| Database | `LogInsights` |
| Container | `log_entries` |
| Partition key | `/component` |
| Throughput | 400 RU/s (provisioned) |

**Constraints**: Key-based auth for POC; public network access enabled; no vector search in this feature (deferred).

## Project Structure (additions)

```text
stockAiApp/
├── .env.example
├── .env                 # local only, gitignored
├── src/
│   ├── cosmos_store.py  # client, ingest, load
│   ├── ingest_cosmos.py # CLI entry for ingest
│   └── main.py          # --source csv|cosmos
└── specs/002-cosmos-log-store/
```

## Out of scope (later)

- Vector embeddings / DiskANN semantic search on `message`
- Managed identity / Entra auth
- Private endpoints
- Stock market APIs
