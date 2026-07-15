# Enable native Cosmos vector index on log_entries (run after capability propagates).
# Prerequisite: az login; account has EnableNoSQLVectorSearch (may take ~15 minutes after enable).
#
# Usage (from stockAiApp):
#   pwsh ./infra/enable-vector-container.ps1

$ErrorActionPreference = "Stop"
$Account = "cosmos-stockai-poc-ne2"
$Rg = "rg-stockai-poc"
$Db = "LogInsights"
$Container = "log_entries"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Ensuring EnableNoSQLVectorSearch capability..."
az cosmosdb update -g $Rg -n $Account --capabilities EnableNoSQLVectorSearch -o none

Write-Host "Deleting container $Container (data will be re-ingested)..."
az cosmosdb sql container delete --account-name $Account -g $Rg --database-name $Db --name $Container --yes

Write-Host "Creating container with vector embedding + quantizedFlat index..."
az cosmosdb sql container create `
  --account-name $Account `
  --resource-group $Rg `
  --database-name $Db `
  --name $Container `
  --partition-key-path "/component" `
  --throughput 400 `
  --vector-embeddings "@$Here/vector-embeddings.json" `
  --idx "@$Here/vector-idx.json" `
  -o json

Write-Host "Done. Re-ingest embeddings:"
Write-Host "  python -m src.ingest_cosmos"
Write-Host "Then set COSMOS_VECTOR_NATIVE=1 in .env for native VectorDistance queries."
