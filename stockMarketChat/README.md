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

**Azure sign-in runs when the app starts** (and again on first Foundry chat if needed):

1. `dotnet run --project StockMarketChat`
2. If you already ran `az login` (or are signed into Visual Studio), auth is **silent** — no browser.
3. Only if no CLI/VS/env session exists: a **browser** window opens, or a **device code** is printed in the console.
4. Tokens are cached on disk so later runs stay silent.

> If chat shows “demo mode”, Foundry failed or was not selected. Default provider is now `Foundry`. Check the server console for errors and `GET /api/health` (`azureAuthenticated`).

| Setting | Purpose |
|---------|---------|
| `Chat:Foundry:InteractiveLogin` | `true` (default) — allow browser login |
| `Chat:Foundry:TenantId` | Optional; set if your account is multi-tenant |

Credential order: environment → Azure CLI → Visual Studio → PowerShell → Azure Developer CLI → **interactive browser**.

You can still use `az login` beforehand if you prefer a silent CLI token. Ensure you can open the agent in the [Foundry project](https://ai.azure.com). Keep `Chat:Provider` as `Auto` or `Foundry`.

The server calls the Responses API with `agent_reference` for `log-insights-chatbot` (same pattern as `foundryLogAgent/invoke_prompt_agent.py`).

`GET /api/health` reports `azureAuthenticated` and token expiry after warmup.

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

## Ticker tape (Cosmos quotes)

Quotes come from Cosmos (via stock-query-api) and are cached **for 1 day** in layers that **survive app restarts**:

```text
Browser localStorage (Chat UI)
        ↓ miss
GET /api/ticker
        ↓
MarketDataService
  1. IMemoryCache          (fast, process lifetime)
  2. App_Data/ticker-cache.json  (durable file — survives restart)
  3. stock-query-api → Cosmos
```

Why not cookies? A full quote list is larger than reliable cookie limits (~4KB).  
Why not default ASP.NET session? Session state is in-memory by default, so it is also wiped on restart (same problem as pure memory cache).

| Setting | Purpose |
|---------|---------|
| `Chat:StockQueryApiBaseUrl` | Cosmos-backed stock API base URL |
| `Chat:Ticker:Limit` | Max quotes on the tape (default 20) |
| `Chat:Ticker:CacheFilePath` | Optional override for durable cache file (default `App_Data/ticker-cache.json`) |

To force refresh: delete `StockMarketChat/App_Data/ticker-cache.json` and clear browser key `marketdesk.ticker.v1` (or wait 24h).

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
