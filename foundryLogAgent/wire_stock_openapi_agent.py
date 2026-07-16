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

INSTRUCTIONS = """You are a stock market assistant with OpenAPI tools connected to Azure Cosmos DB.

ALWAYS call tools before answering any question about prices, symbols, exchanges, sectors, or movers.
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
            tool_choice="required",
        ),
    )
    print(f"published {agent.name} v{agent.version} status={agent.status}")

    openai = client.get_openai_client()
    resp = openai.responses.create(
        model="gpt-5-mini",
        input="What is AAPL price from Cosmos?",
        extra_body={
            "agent_reference": {"name": "log-insights-chatbot", "type": "agent_reference"}
        },
    )
    print("SMOKE:", getattr(resp, "output_text", None))


if __name__ == "__main__":
    main()
