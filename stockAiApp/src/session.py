from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class QueryIntent:
    intent_type: str = "unknown"
    filters: dict[str, Any] = field(default_factory=dict)
    aggregate_by: Optional[str] = None
    time_bucket: Optional[str] = None
    refine_previous: bool = False
    chart_type: str = "bar"
    # Natural language for semantic / vector search against message embeddings
    semantic_query: Optional[str] = None
    top_k: int = 10


@dataclass
class QueryResult:
    rows: pd.DataFrame
    total_count: int
    summary: str = ""
    aggregation: Optional[pd.DataFrame] = None
    truncated: bool = False
    full_rows: Optional[pd.DataFrame] = None


@dataclass
class SessionContext:
    last_intent: Optional[QueryIntent] = None
    last_result: Optional[QueryResult] = None
    last_full_rows: Optional[pd.DataFrame] = None
    last_aggregation: Optional[pd.DataFrame] = None
    history: list[str] = field(default_factory=list)

    def record_query(self, query: str) -> None:
        self.history.append(query)
        if len(self.history) > 10:
            self.history = self.history[-10:]