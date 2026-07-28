"""Email classification normalization and deterministic fallback rules."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .utils import compact_whitespace, parse_iso_datetime

ALLOWED_TYPES = {
    "application_confirmation",
    "assessment_invitation",
    "recruiter_reply",
    "interview_invitation",
    "rejection",
    "offer",
    "referral_confirmation",
    "newsletter",
    "unknown",
}

EMPTY_RESULT = {
    "type": "unknown",
    "company": "",
    "job_title": "",
    "job_id": "",
    "location": "",
    "careers_url": "",
    "application_date": "",
    "confidence": "low",
}

TYPE_PATTERNS = [
    ("offer", [r"\boffer\b", r"offer letter", r"employment offer"]),
    ("rejection", [r"not move forward", r"not moving forward", r"other candidates", r"unfortunately"]),
    ("interview_invitation", [r"\binterview\b", r"schedule (a|your) call", r"availability"]),
    ("assessment_invitation", [r"\bassessment\b", r"coding challenge", r"take[- ]home", r"technical screen"]),
    ("referral_confirmation", [r"\breferral\b", r"referred you", r"referral submitted"]),
    ("application_confirmation", [r"thank you for applying", r"application received", r"received your application", r"application has been submitted"]),
    ("recruiter_reply", [r"thanks for reaching out", r"thank you for reaching out", r"following up", r"re:\s"]),
]

NEWSLETTER_PATTERNS = [
    r"\bunsubscribe\b",
    r"\bnewsletter\b",
    r"\bdigest\b",
    r"view in browser",
    r"manage your preferences",
]

JOB_SIGNAL_PATTERNS = [
    r"application",
    r"interview",
    r"assessment",
    r"job id",
    r"requisition",
    r"position",
    r"role",
]


def classify_email(subject: str, body: str, received_at: str | None = None) -> dict[str, str]:
    """Classify an email with conservative deterministic rules.

    n8n can use this as a fallback or as a post-processor for local model output.
    The function only returns fields supported by the input text.
    """

    subject = compact_whitespace(subject)
    body = body or ""
    text = f"{subject}\n{body}"
    lowered = text.lower()

    result = dict(EMPTY_RESULT)
    result["type"] = _detect_type(lowered)
    result["company"] = _extract_company(subject, body)
    result["job_title"] = _extract_job_title(subject, body)
    result["job_id"] = _extract_job_id(text)
    result["location"] = _extract_labeled_value(text, ["location", "job location"])
    result["careers_url"] = _extract_careers_url(text)
    result["application_date"] = _application_date(received_at)
    result["confidence"] = _confidence(result)
    return result


def normalize_classification(payload: dict[str, Any] | str | None, subject: str = "", body: str = "", received_at: str | None = None) -> dict[str, str]:
    """Normalize local-model JSON into the classification contract."""

    fallback = classify_email(subject, body, received_at)
    parsed: dict[str, Any]
    if payload is None:
        parsed = {}
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = {}
    else:
        parsed = payload

    result = dict(fallback)
    for key in EMPTY_RESULT:
        value = parsed.get(key)
        if value is None:
            continue
        normalized = compact_whitespace(str(value))
        if normalized:
            result[key] = normalized

    if result["type"] not in ALLOWED_TYPES:
        result["type"] = fallback["type"]
    if result["confidence"] not in {"low", "medium", "high"}:
        result["confidence"] = fallback["confidence"]
    return result


def _detect_type(lowered: str) -> str:
    has_newsletter = any(re.search(pattern, lowered) for pattern in NEWSLETTER_PATTERNS)
    has_job_signal = any(re.search(pattern, lowered) for pattern in JOB_SIGNAL_PATTERNS)
    if has_newsletter and not has_job_signal:
        return "newsletter"

    for email_type, patterns in TYPE_PATTERNS:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return email_type
    return "unknown"


def _extract_company(subject: str, body: str) -> str:
    text = f"{subject}\n{body}"
    patterns = [
        r"thank you for applying to\s+([A-Z][A-Za-z0-9&.,'\- ]+?)(?:\.|,|\n|$)",
        r"your application (?:to|with|at)\s+([A-Z][A-Za-z0-9&.,'\- ]+?)(?:\.|,|\n|$)",
        r"application (?:received|submitted).*?\bat\s+([A-Z][A-Za-z0-9&.,'\- ]+?)(?:\.|,|\n|$)",
        r"\bcompany\s*:\s*([^\n\r]+)",
        r"\bfrom\s+([A-Z][A-Za-z0-9&.,'\- ]+?)\s+(?:careers|jobs|talent)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _clean_entity(match.group(1))
    return ""


def _extract_job_title(subject: str, body: str) -> str:
    text = f"{subject}\n{body}"
    patterns = [
        r"\bjob title\s*:\s*([^\n\r]+)",
        r"\bposition\s*:\s*([^\n\r]+)",
        r"\brole\s*:\s*([^\n\r]+)",
        r"for the\s+([A-Za-z0-9&.,'/+\- ]+?)\s+(?:role|position|job)",
        r"for\s+([A-Za-z0-9&.,'/+\- ]+?)\s+(?:at|with)\s+[A-Z]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_entity(match.group(1))
    return ""


def _extract_job_id(text: str) -> str:
    patterns = [
        r"\bjob\s*id\s*[:#-]?\s*([A-Za-z0-9._-]+)",
        r"\breq(?:uisition)?\s*id\s*[:#-]?\s*([A-Za-z0-9._-]+)",
        r"\brequisition\s*[:#-]?\s*([A-Za-z0-9._-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,#")
    return ""


def _extract_labeled_value(text: str, labels: list[str]) -> str:
    for label in labels:
        match = re.search(rf"\b{re.escape(label)}\s*:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if match:
            return _clean_entity(match.group(1))
    return ""


def _extract_careers_url(text: str) -> str:
    urls = re.findall(r"https?://[^\s)>\"]+", text)
    for url in urls:
        lowered = url.lower()
        if any(token in lowered for token in ["career", "job", "greenhouse", "lever", "workday", "ashby"]):
            return url.rstrip(".,")
    return urls[0].rstrip(".,") if urls else ""


def _application_date(received_at: str | None) -> str:
    parsed = parse_iso_datetime(received_at)
    if parsed:
        return parsed.date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def _confidence(result: dict[str, str]) -> str:
    if result["type"] == "newsletter":
        return "high"
    filled = sum(1 for key in ["company", "job_title", "job_id", "careers_url"] if result.get(key))
    if result["type"] != "unknown" and filled >= 2:
        return "high"
    if result["type"] != "unknown" or filled:
        return "medium"
    return "low"


def _clean_entity(value: str) -> str:
    cleaned = compact_whitespace(value)
    cleaned = re.sub(r"\s+(role|position|job)$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .,-")

