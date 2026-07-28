# Warm Reach Dashboard

Open Warm Reach at `http://localhost:8087/dashboard`.

It reads local SQLite referral records and shows:

- referral ask, draft, reply, referral, and contact counts,
- searchable people and referral context,
- referral ask status controls,
- inbox reply candidates ranked from least to most likely,
- gentle follow-ups for sent asks,
- recent referral activity.

Use **New ask** to save a person, their relationship context, and a possible company or opportunity. Changing an ask status adds referral activity. The reply queue records possible inbound replies against sent asks; reviewing or dismissing one does not change the ask status. None of these dashboard actions sends email, creates a Gmail draft, or activates an n8n workflow.

The dashboard is local-only through the worker's Docker port. Do not expose port `8087` to the public internet without adding authentication and TLS.
