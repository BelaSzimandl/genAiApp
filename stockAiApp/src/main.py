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
    parser.add_argument("--max-rows", type=int, default=20, help="Maximum rows displayed per query")
    return parser


def run_chat(data_path: str, max_rows: int) -> int:
    try:
        df = load_logs(data_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    components = sorted(df["component"].unique().tolist())
    session = SessionContext()

    print("AI Log Insights Chatbot")
    print(f"Loaded {len(df)} log entries from {data_path}")
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

        result = execute_intent(df, intent, max_rows=max_rows, base_df=base_df)
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
    return run_chat(args.data, args.max_rows)


if __name__ == "__main__":
    raise SystemExit(main())