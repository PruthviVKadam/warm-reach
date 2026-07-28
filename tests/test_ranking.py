import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.ranking import rank_recruiter, rank_recruiters


class RankingTests(unittest.TestCase):
    def test_technical_recruiter_caps_at_100_with_explanation(self):
        result = rank_recruiter(
            {
                "name": "Jordan Lee",
                "role": "Senior Technical Recruiter",
                "location": "Newark, NJ",
                "public_email": "jordan@example.com",
                "linkedin_url": "https://linkedin.com/in/jordan",
                "hiring_area": "software engineering",
            },
            company="Acme",
            job_title="Software Engineer",
            location="Newark",
        )

        self.assertEqual(result["score"], 100)
        self.assertIn("technical recruiter", result["score_explanation"])

    def test_role_specificity_orders_candidates(self):
        ranked = rank_recruiters(
            [
                {"name": "A", "role": "HR Generalist"},
                {"name": "B", "role": "Engineering Manager"},
                {"name": "C", "role": "University Recruiter"},
            ],
            job_title="Software Engineer",
        )

        self.assertEqual([item["profile"]["name"] for item in ranked], ["B", "C", "A"])


if __name__ == "__main__":
    unittest.main()

