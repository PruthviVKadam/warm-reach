# Architecture

```mermaid
flowchart LR
    Gmail["Gmail / IMAP"] --> N8N["n8n workflows"]
    N8N --> Worker["Local Python worker"]
    N8N --> SearXNG["SearXNG"]
    N8N --> Crawl4AI["Crawl4AI"]
    Worker --> SQLite["SQLite referral records"]
    Worker --> Ollama["Ollama models"]
    Worker --> Qdrant["Qdrant vector memory"]
    Dashboard["Warm Reach dashboard"] --> Worker
    N8N --> Drafts["Gmail drafts"]
    N8N --> Reports["Daily email report"]
    Appsmith["Optional Appsmith dashboard"] --> SQLite
```

The existing n8n workflows are split by responsibility:

- Email monitoring
- Recruiter research
- Email drafting
- Referral reply monitoring
- CRM updates
- Reminder engine
- Daily reports

The worker keeps custom logic outside n8n so referral writes, follow-up rules, and the built-in dashboard API can be tested with regular unit tests. The dashboard reads local SQLite through the worker; it does not expose the database directly to the browser.
