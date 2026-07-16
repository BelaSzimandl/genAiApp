"""CLI: load sample stock quotes into Azure Cosmos DB."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_stocks.csv"
REQUIRED = [
    "symbol",
    "name",
    "exchange",
    "sector",
    "price",
    "change_pct",
    "volume",
    "currency",
    "as_of",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest stock quotes CSV into Cosmos DB")
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    load_dotenv()

    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database = os.getenv("COSMOS_STOCK_DATABASE", "StockMarket").strip()
    container = os.getenv("COSMOS_STOCK_CONTAINER", "quotes").strip()
    if not endpoint or not key:
        print("Error: COSMOS_ENDPOINT and COSMOS_KEY required", file=sys.stderr)
        return 1

    df = pd.read_csv(args.data)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        print(f"Error: CSV missing columns: {missing}", file=sys.stderr)
        return 1

    client = CosmosClient(endpoint, credential=key)
    cont = client.get_database_client(database).get_container_client(container)

    count = 0
    for _, row in df.iterrows():
        symbol = str(row["symbol"]).strip().upper()
        doc = {
            "id": symbol,
            "symbol": symbol,
            "name": str(row["name"]).strip(),
            "exchange": str(row["exchange"]).strip().upper(),
            "sector": str(row["sector"]).strip(),
            "price": float(row["price"]),
            "change_pct": float(row["change_pct"]),
            "volume": int(row["volume"]),
            "currency": str(row["currency"]).strip().upper(),
            "as_of": str(row["as_of"]).strip(),
            "doc_type": "quote",
        }
        cont.upsert_item(doc)
        count += 1

    print(f"Upserted {count} stock quotes into {database}/{container}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
