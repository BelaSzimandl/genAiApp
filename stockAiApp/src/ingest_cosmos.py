"""CLI: load sample CSV into Azure Cosmos DB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cosmos_store import CosmosConfig, ingest_dataframe, ensure_database_and_container
from .data_loader import load_logs

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_logs.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest log CSV into Azure Cosmos DB")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to log CSV")
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="Create database/container if they do not exist",
    )
    args = parser.parse_args(argv)

    try:
        cfg = CosmosConfig.from_env()
        if args.ensure:
            print(f"Ensuring {cfg.database}/{cfg.container} ...")
            ensure_database_and_container(cfg)
        df = load_logs(args.data)
        print(f"Ingesting {len(df)} rows from {args.data} -> {cfg.endpoint}")
        n = ingest_dataframe(df, cfg)
        print(f"Upserted {n} documents into {cfg.database}/{cfg.container}")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
