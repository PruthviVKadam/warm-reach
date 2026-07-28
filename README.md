# Warm Reach

Warm Reach is a local, self-hosted personal platform for thoughtful referral outreach, built around n8n.

It is designed to:

- keep referral contacts, relationship context, and referral asks together,
- create concise referral email drafts for human approval,
- track draft, sent, replied, referred, and closed outreach states,
- rank possible inbox replies against sent referral asks for review,
- surface respectful follow-ups and relationship activity,
- preserve job or company details as optional context for each ask,
- use Ollama and Qdrant for local retrieval-aware generation,
- create Gmail drafts only after credentials and workflows are configured.

No paid API is required by default.

## Stack

- n8n for orchestration
- Ollama for local chat and embedding models
- Qdrant for vector memory
- SQLite for referral contacts, asks, and activity
- SearXNG for metasearch
- Crawl4AI for crawling public pages
- the built-in Warm Reach dashboard served by the Python worker
- Appsmith as an optional low-code dashboard service
- Python standard-library worker for testable local logic

## Run

```powershell
Copy-Item .env.example .env
docker compose up -d
```

Then open `http://localhost:5678`, create the n8n owner account, add Gmail and SMTP credentials, import the workflows from `n8n/workflows`, and run `.\scripts\repair_n8n_subworkflow_links.ps1` for the legacy job-email workflows. Use the [credential and first-run guide](docs/credentials.md) for the exact steps.

Open Warm Reach at `http://localhost:8087/dashboard`. It reads local referral records, records status changes as referral activity, and does not send email by itself.

See:

- `docs/setup.md`
- `docs/environment.md`
- `docs/gmail.md`
- `docs/smtp.md`
- `docs/workflows.md`
- `docs/workflow_diagram.md`
- `docs/dashboard.md`
- `docs/referral-workflow.md`
- `docs/reply-monitoring.md`
- `docs/models.md`
- `docs/source_policy.md`

## Test

```powershell
python -m unittest
```

## Project Layout

```text
docker/
n8n/
  workflows/
  credentials/
database/
embeddings/
rag/
crm/
prompts/
scripts/
docs/
tests/
README.md
docker-compose.yml
```

## Safety Defaults

- Emails are drafted first and require human approval before sending.
- Credentials stay in `.env` or n8n's credential store.
- Scraping is limited to public pages and authorized sources.
- Duplicate email processing is handled through stable event keys and unique database constraints.
