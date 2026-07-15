from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .data_loader import load_logs
from .intent_parser import parse_intent
from .query_engine import execute_intent
from .response_builder import (
    format_chart_message,
    format_help,
    format_no_chart_context,
    format_response,
    format_unknown,
)
from .session import SessionContext
from .visualizer import save_chart

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_logs.csv"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Log Insights Chatbot POC")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to log CSV file")
    parser.add_argument(
        "--source",
        choices=("csv", "cosmos"),
        default="csv",
        help="Load logs from local CSV or Azure Cosmos DB",
    )
    parser.add_argument("--max-rows", type=int, default=20, help="Maximum rows displayed per query")
    return parser


def load_dataframe(source: str, data_path: str):
    if source == "cosmos":
        from .cosmos_store import load_logs_from_cosmos

        return load_logs_from_cosmos(), "Azure Cosmos DB"
    return load_logs(data_path), data_path


def _run_semantic_search(intent, source: str, df, max_rows: int):
    """Vector search via Cosmos when available; local cosine on CSV embeddings otherwise."""
    query = intent.semantic_query or ""
    top_k = intent.top_k or max_rows

    if source == "cosmos":
        from .cosmos_store import vector_search

        return vector_search(query, top_k=top_k)

    # CSV mode: embed messages in-memory with the same model
    from .embeddings import embed_text
    import numpy as np

    q = np.asarray(embed_text(query), dtype=float)
    q = q / (np.linalg.norm(q) or 1.0)
    scores = []
    for idx, row in df.iterrows():
        text = f"{row['component']} {row['log_level']} {row['system_name']} {row['message']}"
        v = np.asarray(embed_text(text), dtype=float)
        v = v / (np.linalg.norm(v) or 1.0)
        distance = 1.0 - float(np.dot(q, v))
        scores.append((idx, distance))
    scores.sort(key=lambda x: x[1])
    top_idx = [i for i, _ in scores[:top_k]]
    distances = {i: d for i, d in scores[:top_k]}
    out = df.loc[top_idx].copy()
    out["similarity"] = [distances[i] for i in top_idx]
    out = out.reset_index(drop=True)
    out.attrs["vector_backend"] = "local_csv"
    return out


def run_chat(data_path: str, max_rows: int, source: str = "csv") -> int:
    try:
        df, source_label = load_dataframe(source, data_path)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if df.empty:
        print(
            "Error: No log entries loaded. If using --source cosmos, run: python -m src.ingest_cosmos",
            file=sys.stderr,
        )
        return 1

    components = sorted(df["component"].unique().tolist())
    session = SessionContext()

    print("AI Log Insights Chatbot")
    print(f"Loaded {len(df)} log entries from {source_label}")
    print("Type 'help' for examples or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0

        if not user_input:
            continue

        lower = user_input.lower()
        if lower in {"quit", "exit"}:
            print("Goodbye.")
            return 0

        session.record_query(user_input)
        intent = parse_intent(user_input, available_components=components)

        if intent.intent_type == "help":
            print(format_help())
            continue

        if intent.intent_type == "visualize":
            if session.last_aggregation is None or session.last_aggregation.empty:
                print(format_no_chart_context())
                continue
            try:
                chart_path = save_chart(session.last_aggregation, OUTPUT_DIR, intent.chart_type)
                print(format_chart_message(str(chart_path)))
            except ValueError as exc:
                print(f"Error: {exc}")
            continue

        if intent.intent_type == "unknown":
            print(format_unknown())
            continue

        base_df = None
        if intent.intent_type == "follow_up" and session.last_full_rows is not None:
            base_df = session.last_full_rows

        semantic_df = None
        if intent.intent_type == "semantic":
            try:
                semantic_df = _run_semantic_search(intent, source, df, max_rows)
            except Exception as exc:  # noqa: BLE001 — surface to user
                print(f"Semantic search error: {exc}")
                continue

        result = execute_intent(
            df, intent, max_rows=max_rows, base_df=base_df, semantic_df=semantic_df
        )
        session.last_intent = intent
        session.last_result = result
        if result.full_rows is not None:
            session.last_full_rows = result.full_rows
        if result.aggregation is not None:
            session.last_aggregation = result.aggregation

        print(format_response(result))
        print()

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_chat(args.data, args.max_rows, source=args.source)


if __name__ == "__main__":
    raise SystemExit(main())