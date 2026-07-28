"""HTTP worker used by n8n workflows."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .classification import classify_email, normalize_classification
from .crm import (
    connect,
    create_referral_ask,
    daily_report_snapshot,
    init_database,
    list_followup_candidates,
    match_referral_reply_candidates,
    queue_embedding,
    record_timeline_event,
    referral_dashboard_snapshot,
    save_referral_draft,
    upsert_application,
    upsert_followup,
    update_application_status,
    update_referral_ask_status,
    update_referral_reply_candidate_review,
)
from .followups import recommend_follow_up
from .rag import search_memory
from .ranking import rank_recruiters


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "WarmReachWorker/0.2"

    def do_GET(self) -> None:
        parsed_url = urlsplit(self.path)
        path = parsed_url.path.rstrip("/") or "/"
        if path == "/health":
            self._send_json({"ok": True})
            return
        if path == "/dashboard":
            self._send_dashboard_asset("index.html", "text/html; charset=utf-8")
            return
        if path == "/dashboard/assets/dashboard.css":
            self._send_dashboard_asset("dashboard.css", "text/css; charset=utf-8")
            return
        if path == "/dashboard/assets/dashboard.js":
            self._send_dashboard_asset("dashboard.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/dashboard":
            query = parse_qs(parsed_url.query)
            with connect() as conn:
                snapshot = referral_dashboard_snapshot(
                    conn,
                    query=self._query_value(query, "query"),
                    status=self._query_value(query, "status"),
                    limit=self._query_limit(query),
                )
            self._send_json(snapshot)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            result = self._route(payload)
            self._send_json(result)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # n8n needs JSON errors for retry branches.
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _route(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = urlsplit(self.path).path.rstrip("/")
        if path == "/classify":
            return classify_email(
                subject=str(payload.get("subject", "")),
                body=str(payload.get("body", "")),
                received_at=payload.get("received_at"),
            )
        if path == "/normalize-classification":
            return normalize_classification(
                payload.get("classification"),
                subject=str(payload.get("subject", "")),
                body=str(payload.get("body", "")),
                received_at=payload.get("received_at"),
            )
        if path == "/rank-recruiters":
            return {
                "recruiters": rank_recruiters(
                    recruiters=list(payload.get("recruiters") or []),
                    company=str(payload.get("company", "")),
                    job_title=str(payload.get("job_title", "")),
                    location=str(payload.get("location", "")),
                )
            }
        if path == "/follow-up":
            return recommend_follow_up(
                last_sent_at=str(payload.get("last_sent_at", "")),
                now=payload.get("now"),
                reply_text=payload.get("reply_text"),
                sent_followups=list(payload.get("sent_followups") or []),
            )
        if path == "/rag/search":
            return search_memory(query=str(payload.get("query", "")), limit=int(payload.get("limit", 5)))
        if path == "/crm/init":
            db = init_database()
            return {"ok": True, "db_path": str(db)}
        if path == "/crm/application":
            with connect() as conn:
                app_id = upsert_application(conn, payload)
                conn.commit()
            return {"ok": True, "application_id": app_id}
        if path == "/crm/timeline":
            with connect() as conn:
                event_id = record_timeline_event(
                    conn,
                    application_id=str(payload["application_id"]),
                    event_key=str(payload["event_key"]),
                    event_type=str(payload["event_type"]),
                    title=str(payload["title"]),
                    details=payload.get("details") or {},
                )
                conn.commit()
            return {"ok": True, "event_id": event_id}
        if path == "/crm/queue-embedding":
            with connect() as conn:
                queue_id = queue_embedding(
                    conn,
                    source_table=str(payload["source_table"]),
                    source_id=str(payload["source_id"]),
                    text=str(payload["text"]),
                )
                conn.commit()
            return {"ok": True, "queue_id": queue_id}
        if path == "/crm/followup-candidates":
            with connect() as conn:
                candidates = list_followup_candidates(conn)
            return {"candidates": candidates}
        if path == "/crm/followup":
            with connect() as conn:
                followup_id = upsert_followup(conn, payload)
                conn.commit()
            return {"ok": True, "followup_id": followup_id}
        if path == "/crm/daily-report":
            with connect() as conn:
                snapshot = daily_report_snapshot(conn)
            return snapshot
        if path == "/api/dashboard/application-status":
            with connect() as conn:
                application = update_application_status(
                    conn,
                    application_id=str(payload.get("application_id") or ""),
                    status=str(payload.get("status") or ""),
                )
                conn.commit()
            return {"ok": True, "application": application}
        if path == "/api/referral-asks":
            with connect() as conn:
                referral_ask = create_referral_ask(conn, payload)
                conn.commit()
            return {"ok": True, "referral_ask": referral_ask}
        if path == "/api/referral-asks/status":
            with connect() as conn:
                referral_ask = update_referral_ask_status(
                    conn,
                    referral_ask_id=str(payload.get("referral_ask_id") or ""),
                    status=str(payload.get("status") or ""),
                )
                conn.commit()
            return {"ok": True, "referral_ask": referral_ask}
        if path == "/api/referral-asks/draft":
            with connect() as conn:
                referral_ask = save_referral_draft(
                    conn,
                    referral_ask_id=str(payload.get("referral_ask_id") or ""),
                    draft_subject=str(payload.get("draft_subject") or ""),
                    draft_body=str(payload.get("draft_body") or ""),
                )
                conn.commit()
            return {"ok": True, "referral_ask": referral_ask}
        if path == "/api/referral-replies/match":
            with connect() as conn:
                candidates = match_referral_reply_candidates(conn, payload)
                conn.commit()
            return {"ok": True, "candidates": candidates}
        if path == "/api/referral-replies/review":
            with connect() as conn:
                candidate = update_referral_reply_candidate_review(
                    conn,
                    candidate_id=str(payload.get("candidate_id") or ""),
                    review_status=str(payload.get("review_status") or ""),
                )
                conn.commit()
            return {"ok": True, "candidate": candidate}
        return {"error": f"unknown endpoint {self.path}"}

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_dashboard_asset(self, filename: str, content_type: str) -> None:
        asset_path = Path(__file__).with_name("dashboard") / filename
        if not asset_path.is_file():
            self._send_json({"error": "dashboard asset not found"}, status=404)
            return
        body = asset_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _query_value(query: dict[str, list[str]], key: str) -> str:
        return str(query.get(key, [""])[0])

    @staticmethod
    def _query_limit(query: dict[str, list[str]]) -> int:
        try:
            return int(query.get("limit", ["100"])[0])
        except ValueError:
            return 100


def run() -> None:
    init_database()
    host = os.getenv("WORKER_HOST", "0.0.0.0")
    port = int(os.getenv("WORKER_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), WorkerHandler)
    print(f"worker listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
