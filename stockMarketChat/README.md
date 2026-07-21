# MarketDesk — Stock Market Chat (Blazor WebAssembly)

.NET **10** Blazor Web App with **Interactive WebAssembly** chat UI, themed as a stock-market trading desk. The browser talks to a same-origin `/api/chat` proxy so secrets never ship in the WASM bundle.

Connects to the existing **Foundry** agent `log-insights-chatbot` (Cosmos stock quotes via OpenAPI tool), with optional **SpaceXAI** fallback and a **demo** mode that can hit the public stock query API.

## Architecture

```text
Browser (Blazor WASM chat UI)
        │  POST /api/chat
        ▼
ASP.NET Core host (StockMarketChat)
        │
        ├─ Foundry agent  log-insights-chatbot  (DefaultAzureCredential)
        │         └─ stock-query-api-bsz → Cosmos StockMarket/quotes
        ├─ SpaceXAI (XAI_API_KEY) optional
        └─ Demo mode (stock API + guidance)
```

Related repo context:

| Piece | Location |
|-------|----------|
| Foundry agent docs | `foundryLogAgent/README.md` |
| Stock query API | `stockQueryApi/` |
| Specs / CLI chatbot | `stockAiApp/specs/` |

## Run

```powershell
cd stockMarketChat
dotnet run --project StockMarketChat
```

Open the HTTPS URL from the console (see `Properties/launchSettings.json`), then go to **Chat**.

Health check: `GET /api/health`

## Configure the chatbot backend

`StockMarketChat/appsettings.json`:

| Setting | Purpose |
|---------|---------|
| `Chat:Provider` | `Auto` (default), `Foundry`, `SpaceXAI`, or `Demo` |
| `Chat:Foundry:ProjectEndpoint` | Foundry project endpoint |
| `Chat:Foundry:AgentName` | `log-insights-chatbot` |
| `Chat:Foundry:Model` | e.g. `gpt-5-mini` |
| `Chat:SpaceXAI:ApiKey` or env `XAI_API_KEY` | SpaceXAI / xAI key (server only) |
| `Chat:StockQueryApiBaseUrl` | Demo / reference stock API |

### Foundry (recommended — full stock agent with tools)

1. `az login` (or use a managed identity in Azure).
2. Ensure you can open the agent in the [Foundry project](https://ai.azure.com).
3. Keep `Chat:Provider` as `Auto` or set to `Foundry`.

The server calls the Responses API with `agent_reference` for `log-insights-chatbot` (same pattern as `foundryLogAgent/invoke_prompt_agent.py`).

### SpaceXAI

```powershell
$env:XAI_API_KEY = "your-key"
# optional: "Chat:Provider": "SpaceXAI"
dotnet run --project StockMarketChat
```

SpaceXAI answers in a market-desk persona but does **not** automatically invoke the Cosmos OpenAPI tool unless you add tools separately.

### Demo mode

If neither Foundry nor SpaceXAI is usable, the API returns demo guidance and may call `stock-query-api-bsz` for simple symbol/list queries.

## Example questions

- What is the price of AAPL?
- Show NASDAQ technology stocks
- Top gainers
- Energy stocks on NYSE
- List exchanges
- Filter stocks down more than 1%

## Project layout

```text
stockMarketChat/
├── StockMarketChat.sln
├── StockMarketChat/                 # ASP.NET Core host + API
│   ├── Services/ChatService.cs
│   ├── Components/                  # Layout, home
│   └── wwwroot/app.css              # Market theme
└── StockMarketChat.Client/          # Blazor WASM
    ├── Pages/Chat.razor             # Chat window
    └── Models/ChatDtos.cs
```

## Notes

- Rate limits on `gpt-5-mini` can be low; wait between messages if you see 429s.
- Do not put API keys in the Client project or `wwwroot`.
