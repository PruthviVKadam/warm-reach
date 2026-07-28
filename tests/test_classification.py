import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.classification import classify_email, normalize_classification


class ClassificationTests(unittest.TestCase):
    def test_application_confirmation_extracts_job_fields(self):
        result = classify_email(
            "Thank you for applying to Acme Inc.",
            "Position: Backend Engineer\nJob ID: BE-123\nLocation: Newark, NJ\nhttps://acme.example/careers/jobs/BE-123",
            "2026-07-01T12:00:00+00:00",
        )

        self.assertEqual(result["type"], "application_confirmation")
        self.assertEqual(result["company"], "Acme Inc")
        self.assertEqual(result["job_title"], "Backend Engineer")
        self.assertEqual(result["job_id"], "BE-123")
        self.assertEqual(result["location"], "Newark, NJ")
        self.assertEqual(result["application_date"], "2026-07-01")
        self.assertEqual(result["confidence"], "high")

    def test_newsletter_without_job_signal_is_ignored(self):
        result = classify_email(
            "Weekly hiring digest",
            "View in browser. Manage your preferences. Unsubscribe.",
            "2026-07-01T12:00:00+00:00",
        )

        self.assertEqual(result["type"], "newsletter")
        self.assertEqual(result["confidence"], "high")

    def test_normalize_rejects_unknown_type(self):
        result = normalize_classification(
            {"type": "made_up", "company": "Acme", "confidence": "certain"},
            "Thank you for applying to Acme.",
            "Position: Data Analyst",
            "2026-07-01T12:00:00+00:00",
        )

        self.assertEqual(result["type"], "application_confirmation")
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["company"], "Acme")


if __name__ == "__main__":
    unittest.main()
