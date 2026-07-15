# Tasks: Azure Cosmos DB Log Store

## Phase 1: Azure provisioning

- [x] T001 Install Azure CLI and authenticate
- [x] T002 Register `Microsoft.DocumentDB` on subscription
- [x] T003 Create resource group `rg-stockai-poc`
- [x] T004 Create Cosmos account `cosmos-stockai-poc-ne2` (Sweden Central)
- [x] T005 Create database `LogInsights` and container `log_entries` (PK `/component`, 400 RU/s)

## Phase 2: Application integration

- [x] T006 Add `azure-cosmos` and `python-dotenv` to requirements.txt
- [x] T007 Add `.env.example` and local `.env` (gitignored)
- [x] T008 Implement `src/cosmos_store.py` (config, ingest, load)
- [x] T009 Implement `src/ingest_cosmos.py` CLI
- [x] T010 Extend `src/main.py` with `--source cosmos`
- [x] T011 Install deps, ingest sample CSV, verify chatbot against Cosmos

## Phase 3: Docs

- [x] T012 Update stockAiApp README with Cosmos setup and portal links

## Phase 4: Vector search on message

- [x] T013 Enable account capability `EnableNoSQLVectorSearch` (propagation may lag)
- [x] T014 Add local embeddings module (`fastembed` 384-d) in `src/embeddings.py`
- [x] T015 Store `embedding` on ingest; vector search in `src/cosmos_store.py`
- [x] T016 Semantic intent + chatbot wiring (`semantic` queries)
- [x] T017 Add `infra/vector-*.json` and `enable-vector-container.ps1` for native index
- [x] T018 Verify semantic ranking against sample corpus (local_cosine backend)
