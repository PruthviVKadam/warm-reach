"""Follow-up recommendation rules."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .utils import parse_iso_datetime

FOLLOW_UP_RULES = [
    (5, "first_follow_up", "No recruiter reply after 5 days"),
    (10, "second_follow_up", "No recruiter reply after 10 days"),
    (20, "final_follow_up", "No recruiter reply after 20 days"),
]


def recommend_follow_up(
    last_sent_at: str,
    now: str | None = None,
    reply_text: str | None = None,
    sent_followups: list[str] | None = None,
) -> dict[str, Any]:
    sent_dt = parse_iso_datetime(last_sent_at)
    if sent_dt is None:
        return {"action": "none", "reason": "Missing or invalid last_sent_at"}

    now_dt = parse_iso_datetime(now) or datetime.now(timezone.utc)
    reply_text = reply_text or ""
    reminder = _explicit_reminder(reply_text, now_dt)
    if reminder:
        return reminder
    if reply_text.strip():
        return {"action": "none", "reason": "Recruiter replied; normal follow-up timer is paused"}

    sent_followups = set(sent_followups or [])
    elapsed_days = (now_dt.date() - sent_dt.date()).days

    for day_count, followup_type, reason in reversed(FOLLOW_UP_RULES):
        if elapsed_days >= day_count and followup_type not in sent_followups:
            due_at = sent_dt + timedelta(days=day_count)
            return {
                "action": "suggest_follow_up",
                "followup_type": followup_type,
                "due_at": due_at.date().isoformat(),
                "elapsed_days": elapsed_days,
                "reason": reason,
            }
    return {
        "action": "none",
        "elapsed_days": elapsed_days,
        "reason": "No follow-up threshold reached",
    }


def _explicit_reminder(reply_text: str, now_dt: datetime) -> dict[str, Any] | None:
    lowered = reply_text.lower()
    if re.search(r"reach out (?:again )?next month|follow up next month|check back next month", lowered):
        due_at = _add_one_month(now_dt)
        return {
            "action": "create_reminder",
            "followup_type": "requested_reminder",
            "due_at": due_at.date().isoformat(),
            "reason": "Recruiter asked to reconnect next month",
        }

    match = re.search(r"(?:reach out|follow up|check back).{0,20}\bin\s+(\d+)\s+days?\b", lowered)
    if match:
        days = int(match.group(1))
        due_at = now_dt + timedelta(days=days)
        return {
            "action": "create_reminder",
            "followup_type": "requested_reminder",
            "due_at": due_at.date().isoformat(),
            "reason": f"Recruiter asked to reconnect in {days} days",
        }
    return None


def _add_one_month(value: datetime) -> datetime:
    month = value.month + 1
    year = value.year
    if month == 13:
        month = 1
        year += 1
    day = min(value.day, _days_in_month(year, month))
    return value.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    this_month = datetime(year, month, 1, tzinfo=timezone.utc)
    return (next_month - this_month).days

