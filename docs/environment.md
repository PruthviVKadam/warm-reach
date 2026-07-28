# Environment Variables

Copy `.env.example` to `.env` and edit local values there.

Core variables:

| Variable | Purpose |
| --- | --- |
| `N8N_PORT` | Local n8n port. |
| `N8N_ENCRYPTION_KEY` | Key n8n uses to encrypt credentials. Replace before running. |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | Set to `false` by Docker Compose so the included trusted workflows can resolve their `$env` service URLs and notification settings. |
| `N8N_WEBHOOK_URL` | Public base URL that n8n uses for webhook and OAuth callbacks. Keep `http://localhost:5678/` for local-only use. |
| `OLLAMA_BASE_URL` | Ollama service URL inside Docker. |
| `OLLAMA_CHAT_MODEL` | Local chat model name. |
| `OLLAMA_EMBEDDING_MODEL` | Local embedding model name. |
| `QDRANT_URL` | Qdrant service URL inside Docker. |
| `QDRANT_COLLECTION` | Vector collection for outreach memory. |
| `SEARXNG_BASE_URL` | SearXNG service URL inside Docker. |
| `CRAWL4AI_BASE_URL` | Crawl4AI service URL inside Docker. |
| `CRAWL4AI_API_TOKEN` | Long random token that allows trusted Docker services to call Crawl4AI. Keep it in `.env` only. |
| `CRM_DB_PATH` | SQLite path inside the worker container. |
| `SMTP_FROM_EMAIL` | Sender used for SMTP report and reminder notifications; fallback recipient for Gmail approval notices. |
| `SMTP_FROM_NAME` | Display name for SMTP report and reminder notifications. |
| `NOTIFICATION_EMAIL` | Recipient for Gmail approval notices; overrides the `SMTP_FROM_EMAIL` fallback. |

Optional API keys:

- `HUNTER_API_KEY`
- `APOLLO_API_KEY`
- `ROCKETREACH_API_KEY`

Leave optional keys blank unless you are authorized to use those services.

The current n8n Docker image uses the owner account created in the n8n UI. It does not use the older `N8N_BASIC_AUTH_*` variables. See the [credential and first-run guide](credentials.md) for the exact setup sequence.

The included workflows use `$env` to reach Docker-internal services such as `http://worker:8080`. This local Compose stack sets `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` for that reason. Do not import workflow JSON from untrusted sources into this instance: a workflow permitted to read `$env` could expose values stored in the n8n container environment.
