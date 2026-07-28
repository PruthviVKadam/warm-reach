"""SQLite CRM helpers."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Any

from .utils import stable_id

DEFAULT_DB_PATH = "data/recruiting.db"
DEFAULT_SCHEMA_PATH = "database/schema.sql"
DASHBOARD_APPLICATION_STATUSES = (
    "draft",
    "submitted",
    "outreach",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
)
REFERRAL_ASK_STATUSES = (
    "planned",
    "draft",
    "ready",
    "sent",
    "replied",
    "referred",
    "closed",
)
REFERRAL_REPLY_REVIEW_STATUSES = ("pending", "reviewed", "dismissed")
REFERRAL_REPLY_STOP_WORDS = {
    "about",
    "and",
    "from",
    "have",
    "quick",
    "referral",
    "role",
    "team",
    "that",
    "the",
    "this",
    "with",
    "would",
    "your",
}


def init_database(db_path: str | Path | None = None, schema_path: str | Path | None = None) -> Path:
    db = Path(db_path or os.getenv("CRM_DB_PATH", DEFAULT_DB_PATH))
    schema = Path(schema_path or os.getenv("CRM_SCHEMA_PATH", DEFAULT_SCHEMA_PATH))
    db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    return db


@contextmanager
def connect(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    db = Path(db_path or os.getenv("CRM_DB_PATH", DEFAULT_DB_PATH))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def table_names(db_path: str | Path) -> set[str]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def upsert_company(conn: sqlite3.Connection, name: str, domain: str = "", careers_url: str = "") -> str:
    company_id = stable_id("company", name)
    conn.execute(
        """
        INSERT INTO companies (id, name, domain, careers_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            domain = COALESCE(NULLIF(excluded.domain, ''), companies.domain),
            careers_url = COALESCE(NULLIF(excluded.careers_url, ''), companies.careers_url),
            updated_at = CURRENT_TIMESTAMP
        """,
        (company_id, name, domain, careers_url),
    )
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
    return str(row["id"])


def upsert_application(conn: sqlite3.Connection, application: dict[str, Any]) -> str:
    company = str(application.get("company") or "").strip()
    if not company:
        raise ValueError("application.company is required")
    company_id = upsert_company(conn, company, careers_url=str(application.get("careers_url") or ""))
    job_title = str(application.get("job_title") or "").strip()
    job_id = str(application.get("job_id") or "").strip()
    application_key = "|".join([company.lower(), job_title.lower(), job_id.lower() or "no-job-id"])
    application_id = stable_id("application", application_key)
    conn.execute(
        """
        INSERT INTO applications (
            id, company_id, company, job_title, job_id, location, careers_url,
            application_date, status, resume_version_id, source_email_id, application_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(application_key) DO UPDATE SET
            job_title = COALESCE(NULLIF(excluded.job_title, ''), applications.job_title),
            job_id = COALESCE(NULLIF(excluded.job_id, ''), applications.job_id),
            location = COALESCE(NULLIF(excluded.location, ''), applications.location),
            careers_url = COALESCE(NULLIF(excluded.careers_url, ''), applications.careers_url),
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            application_id,
            company_id,
            company,
            job_title,
            job_id,
            str(application.get("location") or "").strip(),
            str(application.get("careers_url") or "").strip(),
            str(application.get("application_date") or "").strip(),
            str(application.get("status") or "submitted").strip(),
            str(application.get("resume_version_id") or "").strip() or None,
            str(application.get("source_email_id") or "").strip() or None,
            application_key,
        ),
    )
    row = conn.execute("SELECT id FROM applications WHERE application_key = ?", (application_key,)).fetchone()
    app_id = str(row["id"])
    record_timeline_event(
        conn,
        application_id=app_id,
        event_key=f"{app_id}:application_submitted",
        event_type="application_submitted",
        title="Application Submitted",
        details={"company": company, "job_title": job_title, "job_id": job_id},
    )
    return app_id


def record_timeline_event(
    conn: sqlite3.Connection,
    application_id: str,
    event_key: str,
    event_type: str,
    title: str,
    details: dict[str, Any] | None = None,
) -> str:
    event_id = stable_id("event", event_key)
    conn.execute(
        """
        INSERT INTO timeline (id, application_id, event_key, event_type, title, details_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_key) DO UPDATE SET
            title = excluded.title,
            details_json = excluded.details_json
        """,
        (event_id, application_id, event_key, event_type, title, json.dumps(details or {}, sort_keys=True)),
    )
    return event_id


def queue_embedding(conn: sqlite3.Connection, source_table: str, source_id: str, text: str) -> str:
    queue_id = stable_id("embed", source_table, source_id)
    conn.execute(
        """
        INSERT INTO embeddings_queue (id, source_table, source_id, text)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_table, source_id) DO UPDATE SET
            text = excluded.text,
            status = 'pending',
            error = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (queue_id, source_table, source_id, text),
    )
    return queue_id


def list_followup_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            emails.id AS email_id,
            emails.application_id,
            emails.recruiter_id,
            emails.sent_at AS last_sent_at,
            applications.company,
            applications.job_title,
            recruiters.name AS recruiter_name,
            recruiters.role AS recruiter_role
        FROM emails
        JOIN applications ON applications.id = emails.application_id
        LEFT JOIN recruiters ON recruiters.id = emails.recruiter_id
        LEFT JOIN replies ON replies.email_id = emails.id
        WHERE emails.direction = 'outbound'
          AND emails.status = 'sent'
          AND emails.sent_at IS NOT NULL
          AND replies.id IS NULL
        ORDER BY emails.sent_at ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_followup(conn: sqlite3.Connection, followup: dict[str, Any]) -> str:
    application_id = str(followup.get("application_id") or "").strip()
    followup_type = str(followup.get("followup_type") or "").strip()
    due_at = str(followup.get("due_at") or "").strip()
    if not application_id or not followup_type or not due_at:
        raise ValueError("application_id, followup_type, and due_at are required")
    recruiter_id = str(followup.get("recruiter_id") or "").strip() or None
    followup_id = stable_id("followup", application_id, recruiter_id, followup_type)
    conn.execute(
        """
        INSERT INTO followups (
            id, application_id, recruiter_id, email_id, followup_type, due_at, status, reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(application_id, recruiter_id, followup_type) DO UPDATE SET
            due_at = excluded.due_at,
            status = excluded.status,
            reason = excluded.reason,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            followup_id,
            application_id,
            recruiter_id,
            str(followup.get("email_id") or "").strip() or None,
            followup_type,
            due_at,
            str(followup.get("status") or "suggested").strip(),
            str(followup.get("reason") or "").strip(),
        ),
    )
    return followup_id


def daily_report_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    due_followups = conn.execute(
        """
        SELECT applications.company, applications.job_title, followups.followup_type, followups.due_at, followups.reason
        FROM followups
        JOIN applications ON applications.id = followups.application_id
        WHERE followups.status = 'suggested'
          AND date(followups.due_at) <= date('now')
        ORDER BY followups.due_at ASC
        """
    ).fetchall()
    open_applications = conn.execute(
        """
        SELECT company, job_title, status, application_date
        FROM applications
        WHERE status NOT IN ('rejected', 'offer')
        ORDER BY application_date DESC
        LIMIT 50
        """
    ).fetchall()
    companies_without_outreach = conn.execute(
        """
        SELECT applications.company, applications.job_title
        FROM applications
        LEFT JOIN emails ON emails.application_id = applications.id
            AND emails.direction = 'outbound'
        WHERE emails.id IS NULL
        ORDER BY applications.application_date DESC
        LIMIT 50
        """
    ).fetchall()
    return {
        "due_followups": [dict(row) for row in due_followups],
        "open_applications": [dict(row) for row in open_applications],
        "companies_without_outreach": [dict(row) for row in companies_without_outreach],
    }


def dashboard_snapshot(
    conn: sqlite3.Connection,
    query: str = "",
    status: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Return the CRM data needed by the local recruiting operations dashboard."""

    search = query.strip().lower()
    selected_status = status.strip().lower()
    capped_limit = max(1, min(limit, 100))
    filters: list[str] = []
    parameters: list[Any] = []

    if search:
        like = f"%{search}%"
        filters.append("(LOWER(applications.company) LIKE ? OR LOWER(applications.job_title) LIKE ?)")
        parameters.extend([like, like])
    if selected_status:
        filters.append("applications.status = ?")
        parameters.append(selected_status)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    applications = conn.execute(
        f"""
        SELECT
            applications.id,
            applications.company,
            applications.job_title,
            applications.job_id,
            applications.location,
            applications.careers_url,
            applications.application_date,
            applications.status,
            applications.updated_at,
            (
                SELECT MAX(timeline.event_time)
                FROM timeline
                WHERE timeline.application_id = applications.id
            ) AS last_activity_at,
            (
                SELECT COUNT(*)
                FROM recruiters
                WHERE recruiters.company_id = applications.company_id
            ) AS recruiter_count
        FROM applications
        {where}
        ORDER BY COALESCE(applications.application_date, applications.created_at) DESC, applications.company ASC
        LIMIT ?
        """,
        [*parameters, capped_limit],
    ).fetchall()

    summary = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM applications) AS application_count,
            (
                SELECT COUNT(*)
                FROM applications
                WHERE status NOT IN ('rejected', 'withdrawn')
            ) AS active_application_count,
            (
                SELECT COUNT(*)
                FROM applications
                LEFT JOIN emails ON emails.application_id = applications.id
                    AND emails.direction = 'outbound'
                WHERE emails.id IS NULL
            ) AS outreach_needed_count,
            (
                SELECT COUNT(*)
                FROM followups
                WHERE status = 'suggested'
                  AND date(due_at) <= date('now')
            ) AS due_followup_count,
            (SELECT COUNT(*) FROM recruiters) AS recruiter_count
        """
    ).fetchone()

    followups = conn.execute(
        """
        SELECT
            followups.id,
            followups.application_id,
            followups.followup_type,
            followups.due_at,
            followups.reason,
            applications.company,
            applications.job_title,
            recruiters.name AS recruiter_name,
            recruiters.role AS recruiter_role
        FROM followups
        JOIN applications ON applications.id = followups.application_id
        LEFT JOIN recruiters ON recruiters.id = followups.recruiter_id
        WHERE followups.status = 'suggested'
        ORDER BY followups.due_at ASC
        LIMIT 12
        """
    ).fetchall()

    timeline = conn.execute(
        """
        SELECT
            timeline.id,
            timeline.event_type,
            timeline.event_time,
            timeline.title,
            applications.company,
            applications.job_title
        FROM timeline
        JOIN applications ON applications.id = timeline.application_id
        ORDER BY timeline.event_time DESC, timeline.created_at DESC
        LIMIT 12
        """
    ).fetchall()

    return {
        "summary": dict(summary),
        "applications": [dict(row) for row in applications],
        "followups": [dict(row) for row in followups],
        "timeline": [dict(row) for row in timeline],
        "status_options": list(DASHBOARD_APPLICATION_STATUSES),
    }


def update_application_status(conn: sqlite3.Connection, application_id: str, status: str) -> dict[str, Any]:
    """Update an application status and make the change visible in its timeline."""

    normalized_status = status.strip().lower()
    if normalized_status not in DASHBOARD_APPLICATION_STATUSES:
        allowed = ", ".join(DASHBOARD_APPLICATION_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")

    application = conn.execute(
        "SELECT id, company, job_title, status FROM applications WHERE id = ?",
        (application_id,),
    ).fetchone()
    if not application:
        raise ValueError("application was not found")

    previous_status = str(application["status"])
    if previous_status != normalized_status:
        conn.execute(
            "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (normalized_status, application_id),
        )
        event_key = ":".join(
            [
                application_id,
                "status",
                normalized_status,
                datetime.now(timezone.utc).isoformat(),
            ]
        )
        record_timeline_event(
            conn,
            application_id=application_id,
            event_key=event_key,
            event_type="status_changed",
            title=f"Status changed to {normalized_status}",
            details={"from": previous_status, "to": normalized_status},
        )

    return {
        "id": str(application["id"]),
        "company": str(application["company"]),
        "job_title": str(application["job_title"]),
        "status": normalized_status,
    }


def create_referral_ask(conn: sqlite3.Connection, referral_ask: dict[str, Any]) -> dict[str, Any]:
    """Create or update a personal referral ask and record its first activity."""

    contact_name = str(referral_ask.get("contact_name") or "").strip()
    contact_email = str(referral_ask.get("contact_email") or "").strip().lower()
    if not contact_name or not contact_email:
        raise ValueError("contact_name and contact_email are required")

    contact_organization = str(referral_ask.get("contact_organization") or "").strip()
    relationship_context = str(referral_ask.get("relationship_context") or "").strip()
    company = str(referral_ask.get("company") or "").strip()
    opportunity = str(referral_ask.get("opportunity") or "").strip()
    ask_context = str(referral_ask.get("ask_context") or "").strip()
    next_followup_at = str(referral_ask.get("next_followup_at") or "").strip() or None
    normalized_status = str(referral_ask.get("status") or "planned").strip().lower()
    if normalized_status not in REFERRAL_ASK_STATUSES:
        allowed = ", ".join(REFERRAL_ASK_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")

    contact_key = contact_email
    contact_id = stable_id("referral_contact", contact_key)
    conn.execute(
        """
        INSERT INTO referral_contacts (
            id, contact_key, name, email, organization, relationship_context
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(contact_key) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            organization = COALESCE(NULLIF(excluded.organization, ''), referral_contacts.organization),
            relationship_context = COALESCE(
                NULLIF(excluded.relationship_context, ''), referral_contacts.relationship_context
            ),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            contact_id,
            contact_key,
            contact_name,
            contact_email,
            contact_organization,
            relationship_context,
        ),
    )
    contact = conn.execute(
        "SELECT id, name, email FROM referral_contacts WHERE contact_key = ?",
        (contact_key,),
    ).fetchone()
    contact_id = str(contact["id"])

    referral_key = "|".join(
        [
            contact_key,
            company.lower() or "general",
            opportunity.lower() or "general",
        ]
    )
    referral_id = stable_id("referral_ask", referral_key)
    existing = conn.execute(
        "SELECT id FROM referral_asks WHERE referral_key = ?",
        (referral_key,),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO referral_asks (
            id, referral_key, contact_id, company, opportunity, ask_context, status, next_followup_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(referral_key) DO UPDATE SET
            ask_context = COALESCE(NULLIF(excluded.ask_context, ''), referral_asks.ask_context),
            next_followup_at = COALESCE(excluded.next_followup_at, referral_asks.next_followup_at),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            referral_id,
            referral_key,
            contact_id,
            company,
            opportunity,
            ask_context,
            normalized_status,
            next_followup_at,
        ),
    )
    ask = conn.execute(
        """
        SELECT referral_asks.id, referral_asks.status, referral_contacts.name, referral_contacts.email
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        WHERE referral_asks.referral_key = ?
        """,
        (referral_key,),
    ).fetchone()
    if not existing:
        record_referral_activity(
            conn,
            referral_ask_id=str(ask["id"]),
            activity_key=f"{ask['id']}:created",
            activity_type="referral_ask_created",
            title="Referral ask added",
            details={"contact": str(ask["name"]), "company": company, "opportunity": opportunity},
        )

    return {
        "id": str(ask["id"]),
        "contact_name": str(ask["name"]),
        "contact_email": str(ask["email"]),
        "status": str(ask["status"]),
    }


def record_referral_activity(
    conn: sqlite3.Connection,
    referral_ask_id: str,
    activity_key: str,
    activity_type: str,
    title: str,
    details: dict[str, Any] | None = None,
) -> str:
    activity_id = stable_id("referral_activity", activity_key)
    conn.execute(
        """
        INSERT INTO referral_activity (
            id, referral_ask_id, activity_key, activity_type, title, details_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(activity_key) DO UPDATE SET
            title = excluded.title,
            details_json = excluded.details_json
        """,
        (activity_id, referral_ask_id, activity_key, activity_type, title, json.dumps(details or {}, sort_keys=True)),
    )
    return activity_id


def _message_words(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", value.lower())
        if token not in REFERRAL_REPLY_STOP_WORDS
    }


def _parse_event_time(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _reply_match_confidence(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    if score >= 25:
        return "low"
    return "unlikely"


def match_referral_reply_candidates(conn: sqlite3.Connection, message: dict[str, Any]) -> list[dict[str, Any]]:
    """Store explainable candidate matches for an inbox message and sent referral asks."""

    raw_sender = str(message.get("from_email") or "").strip()
    _, parsed_sender = parseaddr(raw_sender)
    from_email = (parsed_sender or raw_sender).strip().lower()
    if not from_email or "@" not in from_email:
        raise ValueError("from_email must contain an email address")

    gmail_message_id = str(message.get("gmail_message_id") or "").strip()
    subject = str(message.get("subject") or "").strip()
    body_preview = str(message.get("body_preview") or "").strip()[:4000]
    received_at = str(message.get("received_at") or "").strip()
    message_key = gmail_message_id or "|".join([from_email, subject.lower(), received_at, body_preview[:240]])
    message_words = _message_words(" ".join([subject, body_preview]))
    received_time = _parse_event_time(received_at)

    sent_asks = conn.execute(
        """
        SELECT
            referral_asks.id,
            referral_asks.company,
            referral_asks.opportunity,
            referral_asks.ask_context,
            referral_asks.draft_subject,
            referral_asks.sent_at,
            referral_contacts.name AS contact_name,
            referral_contacts.email AS contact_email
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        WHERE referral_asks.status = 'sent'
        """
    ).fetchall()

    candidates: list[dict[str, Any]] = []
    for ask in sent_asks:
        contact_email = str(ask["contact_email"] or "").strip().lower()
        email_matches = from_email == contact_email
        context_words = _message_words(
            " ".join(
                [
                    str(ask["company"] or ""),
                    str(ask["opportunity"] or ""),
                    str(ask["draft_subject"] or ""),
                ]
            )
        )
        shared_context = sorted(message_words & context_words)
        reasons: list[str] = []
        score = 0

        if email_matches:
            score += 65
            reasons.append("Sender email matches the referral contact.")
        if shared_context:
            context_points = min(20, len(shared_context) * 5)
            score += context_points
            reasons.append(f"Message shares context: {', '.join(shared_context[:4])}.")
        if subject.lower().startswith(("re:", "reply:")):
            score += 5
            reasons.append("Subject appears to be a reply.")
        sent_time = _parse_event_time(str(ask["sent_at"] or ""))
        if sent_time and received_time and received_time >= sent_time:
            score += 10
            reasons.append("Message was received after the ask was sent.")

        # Store only candidates with a direct sender match or at least two context terms.
        if not email_matches and len(shared_context) < 2:
            continue

        score = min(score, 100)
        confidence = _reply_match_confidence(score)
        candidate_key = f"{ask['id']}|{message_key}"
        candidate_id = stable_id("referral_reply_candidate", candidate_key)
        existing = conn.execute(
            "SELECT id, review_status FROM referral_reply_candidates WHERE candidate_key = ?",
            (candidate_key,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO referral_reply_candidates (
                id, candidate_key, referral_ask_id, gmail_message_id, from_email, subject,
                body_preview, received_at, match_score, match_confidence, match_reasons_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_key) DO UPDATE SET
                gmail_message_id = excluded.gmail_message_id,
                from_email = excluded.from_email,
                subject = excluded.subject,
                body_preview = excluded.body_preview,
                received_at = excluded.received_at,
                match_score = excluded.match_score,
                match_confidence = excluded.match_confidence,
                match_reasons_json = excluded.match_reasons_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                candidate_id,
                candidate_key,
                str(ask["id"]),
                gmail_message_id or None,
                from_email,
                subject,
                body_preview,
                received_at or None,
                score,
                confidence,
                json.dumps(reasons),
            ),
        )
        if not existing:
            record_referral_activity(
                conn,
                referral_ask_id=str(ask["id"]),
                activity_key=f"{ask['id']}:reply-candidate:{message_key}",
                activity_type="referral_reply_candidate_added",
                title="Possible referral reply received",
                details={"from_email": from_email, "score": score, "confidence": confidence},
            )
        candidates.append(
            {
                "id": candidate_id,
                "referral_ask_id": str(ask["id"]),
                "contact_name": str(ask["contact_name"]),
                "from_email": from_email,
                "subject": subject,
                "match_score": score,
                "match_confidence": confidence,
                "match_reasons": reasons,
                "review_status": str(existing["review_status"]) if existing else "pending",
            }
        )

    return sorted(candidates, key=lambda candidate: candidate["match_score"])


def update_referral_reply_candidate_review(
    conn: sqlite3.Connection,
    candidate_id: str,
    review_status: str,
) -> dict[str, Any]:
    """Record review of a candidate without changing the related referral ask status."""

    normalized_id = candidate_id.strip()
    normalized_status = review_status.strip().lower()
    if not normalized_id:
        raise ValueError("candidate_id is required")
    if normalized_status not in REFERRAL_REPLY_REVIEW_STATUSES:
        allowed = ", ".join(REFERRAL_REPLY_REVIEW_STATUSES)
        raise ValueError(f"review_status must be one of: {allowed}")

    candidate = conn.execute(
        """
        SELECT id, referral_ask_id, review_status, match_score, match_confidence
        FROM referral_reply_candidates
        WHERE id = ?
        """,
        (normalized_id,),
    ).fetchone()
    if not candidate:
        raise ValueError("referral reply candidate was not found")

    previous_status = str(candidate["review_status"])
    if previous_status != normalized_status:
        conn.execute(
            """
            UPDATE referral_reply_candidates
            SET review_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_status, normalized_id),
        )
        record_referral_activity(
            conn,
            referral_ask_id=str(candidate["referral_ask_id"]),
            activity_key=":".join(
                [normalized_id, "review", normalized_status, datetime.now(timezone.utc).isoformat()]
            ),
            activity_type="referral_reply_candidate_reviewed",
            title=f"Possible reply marked {normalized_status}",
            details={
                "from": previous_status,
                "to": normalized_status,
                "score": int(candidate["match_score"]),
                "confidence": str(candidate["match_confidence"]),
            },
        )

    return {
        "id": str(candidate["id"]),
        "referral_ask_id": str(candidate["referral_ask_id"]),
        "review_status": normalized_status,
        "match_score": int(candidate["match_score"]),
        "match_confidence": str(candidate["match_confidence"]),
    }


def referral_dashboard_snapshot(
    conn: sqlite3.Connection,
    query: str = "",
    status: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Return referral-first data for the Warm Reach dashboard."""

    search = query.strip().lower()
    selected_status = status.strip().lower()
    capped_limit = max(1, min(limit, 100))
    filters: list[str] = []
    parameters: list[Any] = []
    if search:
        like = f"%{search}%"
        filters.append(
            "(" 
            "LOWER(referral_contacts.name) LIKE ? OR "
            "LOWER(referral_contacts.email) LIKE ? OR "
            "LOWER(referral_asks.company) LIKE ? OR "
            "LOWER(referral_asks.opportunity) LIKE ?"
            ")"
        )
        parameters.extend([like, like, like, like])
    if selected_status:
        filters.append("referral_asks.status = ?")
        parameters.append(selected_status)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    asks = conn.execute(
        f"""
        SELECT
            referral_asks.id,
            referral_asks.company,
            referral_asks.opportunity,
            referral_asks.ask_context,
            referral_asks.status,
            referral_asks.next_followup_at,
            referral_asks.updated_at,
            referral_contacts.name AS contact_name,
            referral_contacts.email AS contact_email,
            referral_contacts.organization AS contact_organization,
            referral_contacts.relationship_context,
            (
                SELECT MAX(referral_activity.event_time)
                FROM referral_activity
                WHERE referral_activity.referral_ask_id = referral_asks.id
            ) AS last_activity_at
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        {where}
        ORDER BY referral_asks.updated_at DESC, referral_contacts.name ASC
        LIMIT ?
        """,
        [*parameters, capped_limit],
    ).fetchall()

    summary = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM referral_asks) AS ask_count,
            (
                SELECT COUNT(*) FROM referral_asks
                WHERE status IN ('draft', 'ready')
            ) AS draft_ready_count,
            (SELECT COUNT(*) FROM referral_asks WHERE status = 'sent') AS awaiting_reply_count,
            (SELECT COUNT(*) FROM referral_asks WHERE status = 'referred') AS referral_count,
            (SELECT COUNT(*) FROM referral_contacts) AS contact_count,
            (
                SELECT COUNT(*) FROM referral_reply_candidates
                WHERE review_status = 'pending'
            ) AS pending_reply_candidate_count
        """
    ).fetchone()

    followups = conn.execute(
        """
        SELECT
            referral_asks.id,
            referral_asks.company,
            referral_asks.opportunity,
            referral_asks.next_followup_at,
            referral_asks.ask_context,
            referral_contacts.name AS contact_name
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        WHERE referral_asks.status = 'sent'
          AND referral_asks.next_followup_at IS NOT NULL
          AND date(referral_asks.next_followup_at) <= date('now')
        ORDER BY referral_asks.next_followup_at ASC
        LIMIT 12
        """
    ).fetchall()

    timeline = conn.execute(
        """
        SELECT
            referral_activity.id,
            referral_activity.activity_type,
            referral_activity.event_time,
            referral_activity.title,
            referral_contacts.name AS contact_name,
            referral_asks.company,
            referral_asks.opportunity
        FROM referral_activity
        JOIN referral_asks ON referral_asks.id = referral_activity.referral_ask_id
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        ORDER BY referral_activity.event_time DESC, referral_activity.created_at DESC
        LIMIT 12
        """
    ).fetchall()

    reply_candidates = conn.execute(
        """
        SELECT
            referral_reply_candidates.id,
            referral_reply_candidates.from_email,
            referral_reply_candidates.subject,
            referral_reply_candidates.received_at,
            referral_reply_candidates.match_score,
            referral_reply_candidates.match_confidence,
            referral_reply_candidates.match_reasons_json,
            referral_reply_candidates.review_status,
            referral_contacts.name AS contact_name,
            referral_asks.company,
            referral_asks.opportunity
        FROM referral_reply_candidates
        JOIN referral_asks ON referral_asks.id = referral_reply_candidates.referral_ask_id
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        ORDER BY referral_reply_candidates.match_score ASC, referral_reply_candidates.received_at ASC
        LIMIT 24
        """
    ).fetchall()
    serialized_candidates = []
    for candidate in reply_candidates:
        serialized = dict(candidate)
        try:
            serialized["match_reasons"] = json.loads(serialized.pop("match_reasons_json") or "[]")
        except json.JSONDecodeError:
            serialized["match_reasons"] = []
        serialized_candidates.append(serialized)

    return {
        "summary": dict(summary),
        "asks": [dict(row) for row in asks],
        "followups": [dict(row) for row in followups],
        "timeline": [dict(row) for row in timeline],
        "reply_candidates": serialized_candidates,
        "status_options": list(REFERRAL_ASK_STATUSES),
        "reply_review_options": list(REFERRAL_REPLY_REVIEW_STATUSES),
    }


def update_referral_ask_status(conn: sqlite3.Connection, referral_ask_id: str, status: str) -> dict[str, Any]:
    """Move a referral ask through its outreach lifecycle and record the change."""

    normalized_status = status.strip().lower()
    if normalized_status not in REFERRAL_ASK_STATUSES:
        allowed = ", ".join(REFERRAL_ASK_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")
    ask = conn.execute(
        """
        SELECT referral_asks.id, referral_asks.status, referral_contacts.name, referral_contacts.email
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        WHERE referral_asks.id = ?
        """,
        (referral_ask_id,),
    ).fetchone()
    if not ask:
        raise ValueError("referral ask was not found")

    previous_status = str(ask["status"])
    if previous_status != normalized_status:
        conn.execute(
            """
            UPDATE referral_asks
            SET
                status = ?,
                sent_at = CASE WHEN ? = 'sent' THEN COALESCE(sent_at, CURRENT_TIMESTAMP) ELSE sent_at END,
                replied_at = CASE WHEN ? = 'replied' THEN COALESCE(replied_at, CURRENT_TIMESTAMP) ELSE replied_at END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_status, normalized_status, normalized_status, referral_ask_id),
        )
        event_key = ":".join(
            [referral_ask_id, "status", normalized_status, datetime.now(timezone.utc).isoformat()]
        )
        record_referral_activity(
            conn,
            referral_ask_id=referral_ask_id,
            activity_key=event_key,
            activity_type="referral_status_changed",
            title=f"Referral ask marked {normalized_status}",
            details={"from": previous_status, "to": normalized_status},
        )

    return {
        "id": str(ask["id"]),
        "contact_name": str(ask["name"]),
        "contact_email": str(ask["email"]),
        "status": normalized_status,
    }


def save_referral_draft(
    conn: sqlite3.Connection,
    referral_ask_id: str,
    draft_subject: str,
    draft_body: str,
) -> dict[str, Any]:
    """Store a generated referral draft without changing an already-sent ask."""

    normalized_id = referral_ask_id.strip()
    subject = draft_subject.strip()
    body = draft_body.strip()
    if not normalized_id:
        raise ValueError("referral_ask_id is required")
    if not subject or not body:
        raise ValueError("draft_subject and draft_body are required")

    ask = conn.execute(
        """
        SELECT referral_asks.id, referral_asks.status, referral_contacts.name, referral_contacts.email
        FROM referral_asks
        JOIN referral_contacts ON referral_contacts.id = referral_asks.contact_id
        WHERE referral_asks.id = ?
        """,
        (normalized_id,),
    ).fetchone()
    if not ask:
        raise ValueError("referral ask was not found")

    next_status = "draft" if str(ask["status"]) in {"planned", "draft", "ready"} else str(ask["status"])
    conn.execute(
        """
        UPDATE referral_asks
        SET draft_subject = ?, draft_body = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (subject, body, next_status, normalized_id),
    )
    record_referral_activity(
        conn,
        referral_ask_id=normalized_id,
        activity_key=":".join([normalized_id, "draft", datetime.now(timezone.utc).isoformat()]),
        activity_type="referral_draft_saved",
        title="Referral email draft saved",
        details={"subject": subject},
    )
    return {
        "id": str(ask["id"]),
        "contact_name": str(ask["name"]),
        "contact_email": str(ask["email"]),
        "status": next_status,
    }
