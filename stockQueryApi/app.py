"""Stock market query API backed by Azure Cosmos DB (OpenAPI for Foundry tools)."""

from __future__ import annotations

import os
from typing import Any

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Stock Market Query API",
    description=(
        "Query and filter stock exchange quotes stored in Azure Cosmos DB. "
        "Used by the Foundry log/stock insights chatbot as an OpenAPI tool."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _config() -> dict[str, str]:
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database = os.getenv("COSMOS_STOCK_DATABASE", "StockMarket").strip()
    container = os.getenv("COSMOS_STOCK_CONTAINER", "quotes").strip()
    if not endpoint or not key:
        raise RuntimeError("COSMOS_ENDPOINT and COSMOS_KEY must be set")
    return {
        "endpoint": endpoint,
        "key": key,
        "database": database,
        "container": container,
    }


def _container():
    cfg = _config()
    client = CosmosClient(cfg["endpoint"], credential=cfg["key"])
    return client.get_database_client(cfg["database"]).get_container_client(cfg["container"])


def _clean(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": item.get("symbol"),
        "name": item.get("name"),
        "exchange": item.get("exchange"),
        "sector": item.get("sector"),
        "price": item.get("price"),
        "change_pct": item.get("change_pct"),
        "volume": item.get("volume"),
        "currency": item.get("currency"),
        "as_of": item.get("as_of"),
    }


@app.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "stock-query-api"}


@app.get("/stocks", summary="List or filter stock quotes")
def list_stocks(
    exchange: str | None = Query(None, description="Exchange filter e.g. NASDAQ, NYSE, XETRA"),
    sector: str | None = Query(None, description="Sector filter e.g. Technology, Energy"),
    min_price: float | None = Query(None, description="Minimum price"),
    max_price: float | None = Query(None, description="Maximum price"),
    min_change_pct: float | None = Query(None, description="Minimum change percent (e.g. 1 for gainers)"),
    max_change_pct: float | None = Query(None, description="Maximum change percent (e.g. -1 for losers)"),
    currency: str | None = Query(None, description="Currency filter e.g. USD, EUR"),
    limit: int = Query(25, ge=1, le=100, description="Max rows to return"),
) -> dict[str, Any]:
    """Filter stock exchange quotes in Cosmos DB by exchange, sector, price, and change."""
    try:
        cont = _container()
        items = list(
            cont.query_items(
                query="SELECT * FROM c WHERE c.doc_type = 'quote' OR NOT IS_DEFINED(c.doc_type)",
                enable_cross_partition_query=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Cosmos query failed: {exc}") from exc

    rows = [_clean(i) for i in items]
    if exchange:
        rows = [r for r in rows if str(r.get("exchange", "")).upper() == exchange.upper()]
    if sector:
        rows = [r for r in rows if sector.lower() in str(r.get("sector", "")).lower()]
    if currency:
        rows = [r for r in rows if str(r.get("currency", "")).upper() == currency.upper()]
    if min_price is not None:
        rows = [r for r in rows if float(r.get("price") or 0) >= min_price]
    if max_price is not None:
        rows = [r for r in rows if float(r.get("price") or 0) <= max_price]
    if min_change_pct is not None:
        rows = [r for r in rows if float(r.get("change_pct") or 0) >= min_change_pct]
    if max_change_pct is not None:
        rows = [r for r in rows if float(r.get("change_pct") or 0) <= max_change_pct]

    rows.sort(key=lambda r: float(r.get("change_pct") or 0), reverse=True)
    total = len(rows)
    return {"total": total, "count": min(total, limit), "quotes": rows[:limit]}


@app.get("/stocks/{symbol}", summary="Get one stock quote by symbol")
def get_stock(symbol: str) -> dict[str, Any]:
    """Return a single quote for the ticker symbol (e.g. AAPL, MSFT, SAP)."""
    symbol_u = symbol.strip().upper()
    try:
        cont = _container()
        item = cont.read_item(item=symbol_u, partition_key=symbol_u)
        return _clean(item)
    except CosmosResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol_u}") from exc
    except CosmosHttpResponseError as exc:
        raise HTTPException(status_code=502, detail=f"Cosmos error: {exc.message}") from exc


@app.get("/exchanges", summary="List exchanges with quote counts")
def list_exchanges() -> dict[str, Any]:
    """Aggregate quote counts by exchange."""
    try:
        cont = _container()
        items = list(
            cont.query_items(
                query="SELECT c.exchange FROM c",
                enable_cross_partition_query=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Cosmos query failed: {exc}") from exc

    counts: dict[str, int] = {}
    for item in items:
        ex = str(item.get("exchange") or "UNKNOWN").upper()
        counts[ex] = counts.get(ex, 0) + 1
    return {
        "exchanges": [
            {"exchange": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]
    }


@app.get("/movers", summary="Top gainers or losers by change percent")
def movers(
    direction: str = Query("gainers", description="gainers or losers"),
    limit: int = Query(5, ge=1, le=50),
) -> dict[str, Any]:
    """Return top market movers from Cosmos quotes."""
    result = list_stocks(limit=100)
    quotes = result["quotes"]
    reverse = direction.lower() != "losers"
    quotes = sorted(quotes, key=lambda r: float(r.get("change_pct") or 0), reverse=reverse)
    return {"direction": direction, "count": min(len(quotes), limit), "quotes": quotes[:limit]}
