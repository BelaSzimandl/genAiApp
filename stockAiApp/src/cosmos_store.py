"""Azure Cosmos DB client for log entry ingest, load, and vector search."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError
from dotenv import load_dotenv

from .data_loader import REQUIRED_COLUMNS, VALID_LEVELS
from .embeddings import EMBEDDING_DIM, embed_text

# JSON policy files used when ensuring a vector-capable container
_INFRA = Path(__file__).resolve().parent.parent / "infra"


@dataclass(frozen=True)
class CosmosConfig:
    endpoint: str
    key: str
    database: str
    container: str

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> CosmosConfig:
        if env_path:
            load_dotenv(env_path)
        else:
            root = Path(__file__).resolve().parent.parent
            load_dotenv(root / ".env")
            load_dotenv()

        endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
        key = os.getenv("COSMOS_KEY", "").strip()
        database = os.getenv("COSMOS_DATABASE", "LogInsights").strip()
        container = os.getenv("COSMOS_CONTAINER", "log_entries").strip()

        if not endpoint or not key:
            raise ValueError(
                "COSMOS_ENDPOINT and COSMOS_KEY must be set in environment or stockAiApp/.env"
            )
        return cls(endpoint=endpoint, key=key, database=database, container=container)


def get_container(config: CosmosConfig | None = None):
    cfg = config or CosmosConfig.from_env()
    client = CosmosClient(cfg.endpoint, credential=cfg.key)
    db = client.get_database_client(cfg.database)
    return db.get_container_client(cfg.container), cfg


def row_to_document(row: pd.Series, with_embedding: bool = True) -> dict[str, Any]:
    """Map a CSV/pandas log row to a Cosmos document, optionally with vector embedding."""
    ts = row["Timestamp"]
    if hasattr(ts, "isoformat"):
        ts_str = ts.isoformat()
    else:
        ts_str = str(ts)

    component = str(row["component"]).strip()
    corr_id = str(row.get("corr_id") or "").strip()
    doc_id = corr_id if corr_id else str(uuid.uuid4())
    message = str(row["message"]).strip()

    # Embed message primarily (semantic search target); light component hint for context
    embed_source = f"{message}"

    doc: dict[str, Any] = {
        "id": doc_id,
        "Timestamp": ts_str,
        "system_name": str(row["system_name"]).strip(),
        "component": component,
        "log_level": str(row["log_level"]).strip().upper(),
        "corr_id": corr_id,
        "user_ID": str(row.get("user_ID") or "").strip(),
        "message": message,
    }
    if with_embedding:
        doc["embedding"] = embed_text(embed_source)
    return doc


def ingest_dataframe(
    df: pd.DataFrame,
    config: CosmosConfig | None = None,
    with_embedding: bool = True,
) -> int:
    """Upsert all log rows into Cosmos. Returns count of documents written."""
    container, _ = get_container(config)
    count = 0
    for _, row in df.iterrows():
        doc = row_to_document(row, with_embedding=with_embedding)
        container.upsert_item(doc)
        count += 1
    return count


def load_logs_from_cosmos(config: CosmosConfig | None = None) -> pd.DataFrame:
    """Read all log documents from Cosmos into a pandas DataFrame."""
    container, _ = get_container(config)
    try:
        items = list(
            container.query_items(
                query="SELECT c.Timestamp, c.system_name, c.component, c.log_level, c.corr_id, c.user_ID, c.message FROM c",
                enable_cross_partition_query=True,
            )
        )
    except CosmosHttpResponseError as exc:
        raise RuntimeError(f"Cosmos query failed: {exc.message}") from exc

    return _items_to_dataframe(items)


def vector_search(
    query_text: str,
    top_k: int = 10,
    config: CosmosConfig | None = None,
) -> pd.DataFrame:
    """Semantic search over message embeddings stored in Cosmos.

    By default ranks with local cosine over document embeddings (works without
    a container vector index). Set COSMOS_VECTOR_NATIVE=1 to use native
    VectorDistance once EnableNoSQLVectorSearch + vector policy are active.
    """
    container, _ = get_container(config)
    embedding = embed_text(query_text)
    k = max(1, min(int(top_k), 50))
    prefer_native = os.getenv("COSMOS_VECTOR_NATIVE", "").strip() in {"1", "true", "yes"}

    if prefer_native:
        query = f"""
        SELECT TOP {k}
            c.Timestamp, c.system_name, c.component, c.log_level,
            c.corr_id, c.user_ID, c.message,
            VectorDistance(c.embedding, @embedding) AS similarity
        FROM c
        ORDER BY VectorDistance(c.embedding, @embedding)
        """
        try:
            items = list(
                container.query_items(
                    query=query,
                    parameters=[{"name": "@embedding", "value": embedding}],
                    enable_cross_partition_query=True,
                )
            )
            df = _items_to_dataframe(items)
            if not df.empty and "similarity" in df.columns:
                df = df.sort_values("similarity", ascending=True).reset_index(drop=True)
            df.attrs["vector_backend"] = "cosmos"
            return df
        except CosmosHttpResponseError:
            pass

    return _vector_search_local(container, embedding, k)


def _vector_search_local(container, embedding: list[float], k: int) -> pd.DataFrame:
    """Rank documents by cosine distance using embeddings stored on items."""
    import numpy as np

    try:
        items = list(
            container.query_items(
                query=(
                    "SELECT c.Timestamp, c.system_name, c.component, c.log_level, "
                    "c.corr_id, c.user_ID, c.message, c.embedding FROM c"
                ),
                enable_cross_partition_query=True,
            )
        )
    except CosmosHttpResponseError as exc:
        raise RuntimeError(f"Cosmos query failed: {exc.message}") from exc

    query_vec = np.asarray(embedding, dtype=float)
    qn = np.linalg.norm(query_vec)
    if qn == 0:
        qn = 1.0
    query_vec = query_vec / qn

    scored: list[dict[str, Any]] = []
    for item in items:
        emb = item.get("embedding")
        if not emb:
            continue
        v = np.asarray(emb, dtype=float)
        vn = np.linalg.norm(v)
        if vn == 0:
            continue
        v = v / vn
        # Cosine distance = 1 - cosine similarity (aligns with Cosmos cosine distance)
        cos_sim = float(np.dot(query_vec, v))
        distance = 1.0 - cos_sim
        scored.append({**item, "similarity": distance})

    scored.sort(key=lambda x: x["similarity"])
    top = scored[:k]
    df = _items_to_dataframe(top)
    if not df.empty and "similarity" in df.columns:
        df = df.sort_values("similarity", ascending=True).reset_index(drop=True)
    df.attrs["vector_backend"] = "local_cosine"
    return df


def _items_to_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
    if not items:
        cols = list(REQUIRED_COLUMNS) + ["similarity"]
        return pd.DataFrame(columns=cols)

    records = []
    for item in items:
        rec = {
            "Timestamp": item.get("Timestamp"),
            "system_name": item.get("system_name", ""),
            "component": item.get("component", ""),
            "log_level": str(item.get("log_level", "")).upper(),
            "corr_id": item.get("corr_id", ""),
            "user_ID": item.get("user_ID", ""),
            "message": item.get("message", ""),
        }
        if "similarity" in item:
            rec["similarity"] = item["similarity"]
        records.append(rec)

    df = pd.DataFrame.from_records(records)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["Timestamp", "system_name", "component", "log_level", "message"])
    df["log_level"] = df["log_level"].astype(str).str.upper().str.strip()
    df = df[df["log_level"].isin(VALID_LEVELS)]
    return df.sort_values("Timestamp", ascending=False).reset_index(drop=True)


def ensure_database_and_container(
    config: CosmosConfig | None = None,
    with_vector: bool = True,
) -> None:
    """Create database/container if missing. Vector policy requires account capability."""
    cfg = config or CosmosConfig.from_env()
    client = CosmosClient(cfg.endpoint, credential=cfg.key)
    db = client.create_database_if_not_exists(id=cfg.database)

    if not with_vector:
        db.create_container_if_not_exists(
            id=cfg.container,
            partition_key=PartitionKey(path="/component"),
            offer_throughput=400,
        )
        return

    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": "/embedding",
                "dataType": "float32",
                "dimensions": EMBEDDING_DIM,
                "distanceFunction": "cosine",
            }
        ]
    }
    indexing_policy = {
        "indexingMode": "consistent",
        "automatic": True,
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [
            {"path": '/"_etag"/?'},
            {"path": "/embedding/*"},
        ],
        "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
    }

    try:
        db.create_container_if_not_exists(
            id=cfg.container,
            partition_key=PartitionKey(path="/component"),
            offer_throughput=400,
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy,
        )
    except TypeError:
        # Older SDK may use different kwargs — fall back to non-vector
        db.create_container_if_not_exists(
            id=cfg.container,
            partition_key=PartitionKey(path="/component"),
            offer_throughput=400,
        )
