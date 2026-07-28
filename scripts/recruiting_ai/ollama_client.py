"""Minimal Ollama HTTP client using the Python standard library."""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import HTTPError
from typing import Any


def generate(prompt: str, model: str | None = None, base_url: str | None = None, timeout: int = 120) -> str:
    payload = {
        "model": model or os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b"),
        "prompt": prompt,
        "stream": False,
    }
    response = _post_json(f"{base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/generate", payload, timeout)
    return str(response.get("response", ""))


def embed(text: str, model: str | None = None, base_url: str | None = None, timeout: int = 120) -> list[float]:
    selected_model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    selected_base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {
        "model": selected_model,
        "input": text,
    }
    try:
        response = _post_json(f"{selected_base_url}/api/embed", payload, timeout)
    except HTTPError as error:
        if error.code != 404:
            raise
        response = _post_json(
            f"{selected_base_url}/api/embeddings",
            {"model": selected_model, "prompt": text},
            timeout,
        )

    embeddings = response.get("embeddings")
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return [float(value) for value in embeddings[0]]

    embedding = response.get("embedding", [])
    if not isinstance(embedding, list):
        raise ValueError("Ollama embedding response did not contain a list")
    if not embedding:
        raise ValueError("Ollama embedding response did not contain values")
    return [float(value) for value in embedding]


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object response")
    return parsed
