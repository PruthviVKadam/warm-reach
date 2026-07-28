# Referral Reply Monitoring

`n8n/workflows/08-referral-reply-monitor.json` is an inactive, inbox-only workflow for Warm Reach. It checks unread Gmail messages, normalizes the sender and message text, and sends those details to the local worker for matching against referral asks marked `sent`.

It never sends an email. It does not automatically change a referral ask to `replied` or `referred`.

## Matching Rules

Each incoming message is evaluated against every sent referral ask. A candidate is stored only when:

- the sender email matches the saved referral contact, or
- the message shares at least two meaningful company, opportunity, or draft-subject terms with a sent ask.

The score is explainable: matching sender address, shared context, reply-style subject, and arrival after the sent timestamp contribute to it. The dashboard lists stored candidates from least to most likely. Use the review control to mark a candidate `reviewed` or `dismissed`; this does not alter the referral ask status.

## Activation

1. Import `08-referral-reply-monitor.json` into n8n.
2. Attach the same Gmail OAuth credential used by the existing Gmail trigger.
3. Keep it inactive until you are ready to monitor new unread inbox messages.
4. Activate it in n8n. It polls unread mail once per minute, matching only against asks marked `sent` in Warm Reach.

It does not backfill historical read email. A future manual backfill should be run separately so its scope can be reviewed before it reads older inbox data.
