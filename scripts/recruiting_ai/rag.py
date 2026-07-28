"""Local retrieval helpers for Qdrant-backed memory."""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import HTTPError
from typing import Any

from .ollama_client import embed
from .qdrant_client import ensure_collection


def search_memory(query: str, limit: int = 5) -> dict[str, Any]:
    if not query.strip():
        return {"matches": [], "reason": "empty query"}
    vector = embed(query)
    collection = os.getenv("QDRANT_COLLECTION", "recruiting_memory")
    base_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    if not _collection_exists(base_url, collection):
        ensure_collection(collection=collection, dimension=len(vector), base_url=base_url)

    payload = {"query": vector, "limit": limit, "with_payload": True}
    request = urllib.request.Request(
        f"{base_url}/collections/{collection}/points/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    result = parsed.get("result", {})
    matches = result.get("points", []) if isinstance(result, dict) else result
    return {"matches": matches}


def _collection_exists(base_url: str, collection: str) -> bool:
    request = urllib.request.Request(f"{base_url}/collections/{collection}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30):
            return True
    except HTTPError as error:
        if error.code == 404:
            return False
        raise
