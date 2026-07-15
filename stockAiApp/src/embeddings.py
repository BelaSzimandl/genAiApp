"""Text embeddings for Cosmos DB vector search.

Default provider: fastembed (BAAI/bge-small-en-v1.5, 384-d) — offline after first download.
Fallback: scikit-learn HashingVectorizer if fastembed is unavailable.
Optional: Azure OpenAI via EMBEDDING_PROVIDER=azure_openai.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

import numpy as np

EMBEDDING_DIM = 384


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
    if provider == "azure_openai":
        return _embed_azure_openai(texts)
    if provider == "hash":
        return _embed_hash(texts)
    if provider in {"auto", "fastembed", "local"}:
        try:
            return _embed_fastembed(texts)
        except Exception:
            if provider == "fastembed":
                raise
            return _embed_hash(texts)
    return _embed_hash(texts)


@lru_cache(maxsize=1)
def _fastembed_model():
    from fastembed import TextEmbedding

    # 384 dimensions — matches Cosmos vector policy
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _embed_fastembed(texts: list[str]) -> list[list[float]]:
    model = _fastembed_model()
    docs = [_normalize_text(t) if t else " " for t in texts]
    vectors = list(model.embed(docs))
    out: list[list[float]] = []
    for vec in vectors:
        arr = np.asarray(vec, dtype=float)
        n = np.linalg.norm(arr)
        if n > 0:
            arr = arr / n
        out.append(arr.tolist())
    return out


@lru_cache(maxsize=1)
def _hash_vectorizer():
    from sklearn.feature_extraction.text import HashingVectorizer

    return HashingVectorizer(
        n_features=EMBEDDING_DIM,
        alternate_sign=False,
        norm=None,
        lowercase=True,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w+\b",
    )


def _embed_hash(texts: list[str]) -> list[list[float]]:
    from sklearn.preprocessing import normalize

    docs = [_normalize_text(t) for t in texts]
    matrix = _hash_vectorizer().transform(docs)
    dense = matrix.astype(np.float64).toarray()
    dense = normalize(dense, norm="l2", axis=1)
    for i, row in enumerate(dense):
        if not np.any(row):
            dense[i] = np.full(EMBEDDING_DIM, 1.0 / np.sqrt(EMBEDDING_DIM))
    return dense.astype(float).tolist()


def _embed_azure_openai(texts: list[str]) -> list[list[float]]:
    try:
        from openai import AzureOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "EMBEDDING_PROVIDER=azure_openai requires 'openai'. pip install openai"
        ) from exc

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01").strip()
    if not endpoint or not key:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set")

    client = AzureOpenAI(azure_endpoint=endpoint, api_key=key, api_version=api_version)
    response = client.embeddings.create(input=texts, model=deployment)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
