"""Minimal Qdrant HTTP helpers."""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import HTTPError
from typing import Any


def ensure_collection(collection: str | None = None, dimension: int | None = None, base_url: str | None = None) -> dict[str, Any]:
    collection = collection or os.getenv("QDRANT_COLLECTION", "recruiting_memory")
    dimension = dimension or int(os.getenv("EMBEDDING_DIMENSION", "768"))
    base_url = base_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    payload = {"vectors": {"size": dimension, "distance": "Cosine"}}
    try:
        return _request_json("PUT", f"{base_url}/collections/{collection}", payload)
    except HTTPError as error:
        if error.code == 409:
            return {"status": "already_exists"}
        raise


def upsert_point(point_id: str, vector: list[float], payload: dict[str, Any], collection: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    collection = collection or os.getenv("QDRANT_COLLECTION", "recruiting_memory")
    base_url = base_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    body = {"points": [{"id": point_id, "vector": vector, "payload": payload}]}
    return _request_json("PUT", f"{base_url}/collections/{collection}/points?wait=true", body)


def _request_json(method: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object response")
    return parsed
