# Stock market chatbot — Azure AI Foundry + Cosmos DB

The Foundry agent **`log-insights-chatbot`** queries **live stock quotes in Cosmos DB** via an OpenAPI tool.

## Architecture

```text
Foundry agent (stock-market-ai / West Europe)
    │  OpenAPI tool (anonymous)
    ▼
App Service: stock-query-api-bsz (West Europe)
    │  Cosmos SDK
    ▼
Cosmos DB: cosmos-stock-market-ai (Poland Central)
    database StockMarket / container quotes
```

All in resource group **`stock-market-ai-rg`**.

## Portal

- Project: [stock-market-ai](https://ai.azure.com/nextgen/r/MKhV0iKbTtKMbbyx_CoFBg,stock-market-ai-rg,,stock-market-ai-resource,stock-market-ai/home)
- Agent: **log-insights-chatbot** (use latest version, currently **v5**)
- Playground: open the agent → Chat

## Ask the chatbot

**Scope:** stock market / exchange quotes only. Off-topic questions (cars, sports, general chat, etc.) are refused with a short redirect to market examples.

In scope (live Cosmos data):

- What is the price of AAPL?
- Show NASDAQ technology stocks
- Top gainers
- Energy stocks on NYSE
- List exchanges
- Filter stocks down more than 1%
- What stock looks worth buying based on recent movers? (informational, not advice)

Out of scope (agent must refuse):

- What type of Ferrari can I buy?
- Non-market general knowledge or shopping questions

## Azure resources

| Resource | Name |
|----------|------|
| RG | `stock-market-ai-rg` |
| Cosmos account | `cosmos-stock-market-ai` |
| Database / container | `StockMarket` / `quotes` |
| Stock API | `https://stock-query-api-bsz.azurewebsites.net` |
| OpenAPI | `https://stock-query-api-bsz.azurewebsites.net/openapi.json` |
| Model | `gpt-5-mini` |

## Data ops

```powershell
cd stockAiApp
.\.venv\Scripts\activate
# upsert sample_stocks.csv into Cosmos
python -m src.ingest_stocks
```

Sample CSV: `stockAiApp/data/sample_stocks.csv` (AAPL, MSFT, NVDA, SAP, SPY, BTC-USD, …).

## API ops

```powershell
# health
curl https://stock-query-api-bsz.azurewebsites.net/health
# filter
curl "https://stock-query-api-bsz.azurewebsites.net/stocks?exchange=NASDAQ&limit=5"
curl https://stock-query-api-bsz.azurewebsites.net/stocks/AAPL
```

Redeploy API after code changes:

```powershell
cd stockQueryApi
Compress-Archive -Path app.py,requirements.txt -DestinationPath deploy.zip -Force
az webapp deploy -g stock-market-ai-rg -n stock-query-api-bsz --src-path deploy.zip --type zip
```

Republish agent tool wiring:

```powershell
cd foundryLogAgent
..\stockAiApp\.venv\Scripts\python.exe .\wire_stock_openapi_agent.py
```

## Rate limits

`gpt-5-mini` on this subscription is provisioned at **capacity 1** (very low RPM). Wait ~1 minute between playground messages if you see rate-limit errors. Request higher OpenAI quota for smoother demos.
