"""Publish Foundry agent with OpenAPI tools over live Cosmos stock quotes."""

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    OpenApiAnonymousAuthDetails,
    OpenApiFunctionDefinition,
    OpenApiTool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential

API = "https://stock-query-api-bsz.azurewebsites.net"
PROJECT = "https://stock-market-ai-resource.services.ai.azure.com/api/projects/stock-market-ai"

# Minimal OpenAPI 3.0.3 for Foundry tool compatibility
SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Stock Market Query API",
        "version": "1.0.0",
        "description": "Live Cosmos DB stock exchange quotes",
    },
    "servers": [{"url": API}],
    "paths": {
        "/stocks": {
            "get": {
                "operationId": "listStocks",
                "summary": "List or filter stock quotes from Cosmos DB",
                "parameters": [
                    {
                        "name": "exchange",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "NASDAQ, NYSE, XETRA, CRYPTO, NYSEARCA",
                    },
                    {
                        "name": "sector",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Technology, Energy, Financials, etc.",
                    },
                    {
                        "name": "min_change_pct",
                        "in": "query",
                        "schema": {"type": "number"},
                    },
                    {
                        "name": "max_change_pct",
                        "in": "query",
                        "schema": {"type": "number"},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 25},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/stocks/{symbol}": {
            "get": {
                "operationId": "getStock",
                "summary": "Get one quote by ticker symbol e.g. AAPL",
                "parameters": [
                    {
                        "name": "symbol",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/movers": {
            "get": {
                "operationId": "getMovers",
                "summary": "Top gainers or losers",
                "parameters": [
                    {
                        "name": "direction",
                        "in": "query",
                        "schema": {
                            "type": "string",
                            "enum": ["gainers", "losers"],
                            "default": "gainers",
                        },
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 5},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
        "/exchanges": {
            "get": {
                "operationId": "listExchanges",
                "summary": "List exchanges with counts",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }
        },
    },
}

INSTRUCTIONS = """You are a stock market assistant only. You help with stocks, tickers, exchanges, sectors, prices, movers, and related market data stored in Azure Cosmos DB (via tools).

## Scope (strict)
IN SCOPE — answer these:
- Stock prices, quotes, tickers (e.g. AAPL, MSFT), exchanges (NASDAQ, NYSE, …), sectors
- Top gainers/losers, filters by change %, exchange, sector
- Which stocks look interesting to buy/hold based on available quote data (always note this is not formal financial advice)
- Lists of exchanges and market data summaries from Cosmos

OUT OF SCOPE — do NOT answer these (cars, sports, recipes, general knowledge, non-market shopping, politics, etc.):
- Example OUT: "What type of Ferrari car can I buy?"
- Example OUT: "Who won the World Cup?" / "Write a poem" / "How do I cook pasta?"

If the user question is not about the stock market / financial instruments / exchange data:
1. Do NOT call tools.
2. Politely refuse in one or two sentences.
3. Say you only answer stock-market questions about the Cosmos quote data.
4. Offer 2–3 example in-scope questions (e.g. "What is the price of AAPL?", "Show NASDAQ technology stocks", "Top gainers").

If the question mixes topics, answer only the stock-market part and ignore the rest.

## Tools
ALWAYS call tools before answering any in-scope question about prices, symbols, exchanges, sectors, or movers.
Never invent prices. After tool results, summarize clearly (symbol, price, change %, exchange, sector, as_of).

Tool map:
- getStock: one ticker (AAPL, MSFT, SAP, BTC-USD, SPY, ...)
- listStocks: filter by exchange / sector / change %
- getMovers: top gainers or losers
- listExchanges: counts by exchange
"""


def main() -> None:
    tool = OpenApiTool(
        openapi=OpenApiFunctionDefinition(
            name="stock_cosmos_api",
            description="Query live stock exchange data stored in Azure Cosmos DB",
            spec=SPEC,
            auth=OpenApiAnonymousAuthDetails(),
        )
    )
    client = AIProjectClient(endpoint=PROJECT, credential=DefaultAzureCredential())
    agent = client.agents.create_version(
        agent_name="log-insights-chatbot",
        definition=PromptAgentDefinition(
            model="gpt-5-mini",
            instructions=INSTRUCTIONS,
            tools=[tool],
            # auto: allow refuse-without-tools for off-topic; still use tools for market Qs
            tool_choice="auto",
        ),
    )
    print(f"published {agent.name} v{agent.version} status={agent.status}")

    openai = client.get_openai_client()
    for label, prompt in [
        ("IN_SCOPE", "What is AAPL price from Cosmos?"),
        ("OUT_OF_SCOPE", "What type of Ferrari car can I buy?"),
    ]:
        resp = openai.responses.create(
            model="gpt-5-mini",
            input=prompt,
            extra_body={
                "agent_reference": {
                    "name": "log-insights-chatbot",
                    "type": "agent_reference",
                }
            },
        )
        print(f"SMOKE[{label}]:", getattr(resp, "output_text", None))


if __name__ == "__main__":
    main()
