import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.crm import (
    connect,
    create_referral_ask,
    dashboard_snapshot,
    init_database,
    match_referral_reply_candidates,
    referral_dashboard_snapshot,
    save_referral_draft,
    table_names,
    update_application_status,
    update_referral_ask_status,
    update_referral_reply_candidate_review,
    upsert_application,
    upsert_followup,
)


class CrmTests(unittest.TestCase):
    def test_schema_initializes_expected_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "recruiting.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            self.assertTrue(
                {
                    "applications",
                    "recruiters",
                    "companies",
                    "emails",
                    "replies",
                    "followups",
                    "notes",
                    "relationships",
                    "timeline",
                    "referral_contacts",
                    "referral_asks",
                    "referral_activity",
                    "referral_reply_candidates",
                }.issubset(table_names(db_path))
            )

    def test_upsert_application_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "recruiting.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                first = upsert_application(
                    conn,
                    {
                        "company": "Acme",
                        "job_title": "Backend Engineer",
                        "job_id": "BE-123",
                        "application_date": "2026-07-01",
                    },
                )
                second = upsert_application(
                    conn,
                    {
                        "company": "Acme",
                        "job_title": "Backend Engineer",
                        "job_id": "BE-123",
                        "application_date": "2026-07-01",
                    },
                )
                conn.commit()

                self.assertEqual(first, second)
                app_count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
                timeline_count = conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0]
                self.assertEqual(app_count, 1)
                self.assertEqual(timeline_count, 1)

    def test_upsert_followup_requires_core_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "recruiting.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                with self.assertRaises(ValueError):
                    upsert_followup(conn, {"application_id": "app_1"})

    def test_dashboard_snapshot_and_status_update_use_real_crm_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "recruiting.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                application_id = upsert_application(
                    conn,
                    {
                        "company": "Acme",
                        "job_title": "Data Engineer",
                        "job_id": "DE-2026",
                        "application_date": "2026-07-28",
                    },
                )
                upsert_followup(
                    conn,
                    {
                        "application_id": application_id,
                        "followup_type": "check_in",
                        "due_at": "2026-07-28",
                        "reason": "Controlled dashboard test",
                    },
                )
                updated = update_application_status(conn, application_id, "interviewing")
                conn.commit()

                snapshot = dashboard_snapshot(conn, query="Acme")

            self.assertEqual(updated["status"], "interviewing")
            self.assertEqual(snapshot["summary"]["application_count"], 1)
            self.assertEqual(snapshot["summary"]["due_followup_count"], 1)
            self.assertEqual(snapshot["applications"][0]["company"], "Acme")
            self.assertEqual(snapshot["applications"][0]["status"], "interviewing")
            self.assertEqual(snapshot["followups"][0]["company"], "Acme")
            self.assertIn("status_changed", [event["event_type"] for event in snapshot["timeline"]])

    def test_referral_dashboard_tracks_personal_outreach_and_followups(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "warm-reach.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                created = create_referral_ask(
                    conn,
                    {
                        "contact_name": "Avery Chen",
                        "contact_email": "avery@example.test",
                        "contact_organization": "NJIT",
                        "relationship_context": "NJIT alumni connection",
                        "company": "Northwind",
                        "opportunity": "Data Scientist role",
                        "ask_context": "Ask for a referral after a short catch-up.",
                        "next_followup_at": "2000-01-01",
                        "status": "ready",
                    },
                )
                drafted = save_referral_draft(
                    conn,
                    created["id"],
                    "Quick referral question",
                    "Hi Avery,\n\nWould you be comfortable referring me?\n\nBest,\nPruthvi Kadam",
                )
                sent = update_referral_ask_status(conn, created["id"], "sent")
                conn.commit()

                sent_snapshot = referral_dashboard_snapshot(conn, query="Avery")
                referred = update_referral_ask_status(conn, created["id"], "referred")
                conn.commit()
                referred_snapshot = referral_dashboard_snapshot(conn, status="referred")

            self.assertEqual(drafted["status"], "draft")
            self.assertEqual(sent["status"], "sent")
            self.assertEqual(sent_snapshot["summary"]["ask_count"], 1)
            self.assertEqual(sent_snapshot["summary"]["awaiting_reply_count"], 1)
            self.assertEqual(sent_snapshot["summary"]["contact_count"], 1)
            self.assertEqual(sent_snapshot["asks"][0]["contact_name"], "Avery Chen")
            self.assertEqual(sent_snapshot["asks"][0]["relationship_context"], "NJIT alumni connection")
            self.assertEqual(sent_snapshot["followups"][0]["company"], "Northwind")
            self.assertIn(
                "referral_status_changed",
                [event["activity_type"] for event in sent_snapshot["timeline"]],
            )
            self.assertIn(
                "referral_draft_saved",
                [event["activity_type"] for event in sent_snapshot["timeline"]],
            )
            self.assertEqual(referred["status"], "referred")
            self.assertEqual(referred_snapshot["summary"]["referral_count"], 1)

    def test_referral_ask_requires_a_contact_and_valid_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "warm-reach.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                with self.assertRaisesRegex(ValueError, "contact_name and contact_email"):
                    create_referral_ask(conn, {"contact_name": "Avery Chen"})
                with self.assertRaisesRegex(ValueError, "status must be one of"):
                    create_referral_ask(
                        conn,
                        {
                            "contact_name": "Avery Chen",
                            "contact_email": "avery@example.test",
                            "status": "queued",
                        },
                    )

    def test_referral_reply_candidates_are_ranked_and_require_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "warm-reach.db"
            init_database(db_path, ROOT / "database" / "schema.sql")

            with connect(db_path) as conn:
                ask = create_referral_ask(
                    conn,
                    {
                        "contact_name": "Avery Chen",
                        "contact_email": "avery@example.test",
                        "company": "Northwind",
                        "opportunity": "Data Scientist role",
                        "status": "planned",
                    },
                )
                save_referral_draft(conn, ask["id"], "Quick referral question", "Controlled test draft")
                update_referral_ask_status(conn, ask["id"], "sent")

                low_matches = match_referral_reply_candidates(
                    conn,
                    {
                        "gmail_message_id": "message-low",
                        "from_email": "unrelated@example.test",
                        "subject": "Northwind Data Scientist",
                        "received_at": "2030-01-01T00:00:00Z",
                    },
                )
                high_matches = match_referral_reply_candidates(
                    conn,
                    {
                        "gmail_message_id": "message-high",
                        "from_email": "Avery Chen <avery@example.test>",
                        "subject": "Re: Quick referral question",
                        "received_at": "2030-01-02T00:00:00Z",
                    },
                )
                repeated_high_matches = match_referral_reply_candidates(
                    conn,
                    {
                        "gmail_message_id": "message-high",
                        "from_email": "avery@example.test",
                        "subject": "Re: Quick referral question",
                        "received_at": "2030-01-02T00:00:00Z",
                    },
                )
                conn.commit()

                snapshot = referral_dashboard_snapshot(conn)
                reviewed = update_referral_reply_candidate_review(
                    conn,
                    candidate_id=low_matches[0]["id"],
                    review_status="dismissed",
                )
                conn.commit()
                updated_snapshot = referral_dashboard_snapshot(conn)
                ask_status = conn.execute(
                    "SELECT status FROM referral_asks WHERE id = ?",
                    (ask["id"],),
                ).fetchone()[0]

            self.assertEqual(len(low_matches), 1)
            self.assertEqual(len(high_matches), 1)
            self.assertEqual(len(repeated_high_matches), 1)
            self.assertLess(low_matches[0]["match_score"], high_matches[0]["match_score"])
            self.assertEqual(high_matches[0]["match_confidence"], "high")
            self.assertEqual([candidate["match_score"] for candidate in snapshot["reply_candidates"]], sorted(
                candidate["match_score"] for candidate in snapshot["reply_candidates"]
            ))
            self.assertEqual(snapshot["summary"]["pending_reply_candidate_count"], 2)
            self.assertEqual(reviewed["review_status"], "dismissed")
            self.assertEqual(updated_snapshot["summary"]["pending_reply_candidate_count"], 1)
            self.assertEqual(ask_status, "sent")
            self.assertIn(
                "referral_reply_candidate_added",
                [event["activity_type"] for event in updated_snapshot["timeline"]],
            )


if __name__ == "__main__":
    unittest.main()
