# Outreach Email Prompt

Generate only the concise variable parts of an outreach email for the selected recruiter. n8n owns the fixed greeting, spacing, sign-off, and sender name.

Inputs:

- Company and job details
- Recruiter profile and score explanation
- Resume version sent for this application
- Retrieved memories: previous conversations, similar companies, prior successful referral emails, recruiter interactions, job descriptions, portfolio notes

Rules:

- Never claim a personal relationship that does not exist.
- Never fabricate experience, metrics, or credentials.
- Keep every generated part short, professional, friendly, and specific.
- Return one relevant portfolio or resume sentence only when it is present in the retrieved context; otherwise return `NONE`.
- Return a clear low-friction ask.
- Do not add a greeting, sign-off, or sender name.

The n8n boilerplate assembles the final body in this order:

```text
Hi {recruiter first name},

{opening sentence}

{relevant point, only when grounded in retrieved context}

{low-friction ask}

Best,
Pruthvi Kadam
```
