import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.followups import recommend_follow_up


class FollowupTests(unittest.TestCase):
    def test_first_followup_after_five_days(self):
        result = recommend_follow_up(
            "2026-07-01T10:00:00+00:00",
            now="2026-07-06T09:00:00+00:00",
        )

        self.assertEqual(result["action"], "suggest_follow_up")
        self.assertEqual(result["followup_type"], "first_follow_up")
        self.assertEqual(result["due_at"], "2026-07-06")

    def test_second_followup_after_first_was_sent(self):
        result = recommend_follow_up(
            "2026-07-01T10:00:00+00:00",
            now="2026-07-11T09:00:00+00:00",
            sent_followups=["first_follow_up"],
        )

        self.assertEqual(result["followup_type"], "second_follow_up")

    def test_explicit_next_month_reminder_pauses_normal_timer(self):
        result = recommend_follow_up(
            "2026-07-01T10:00:00+00:00",
            now="2026-07-27T09:00:00+00:00",
            reply_text="Thanks. Reach out next month.",
        )

        self.assertEqual(result["action"], "create_reminder")
        self.assertEqual(result["due_at"], "2026-08-27")


if __name__ == "__main__":
    unittest.main()

