"""Small shared utilities with no third-party dependencies."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "unknown"


def stable_id(prefix: str, *parts: Any) -> str:
    source = "|".join("" if part is None else str(part).strip().lower() for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def compact_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

