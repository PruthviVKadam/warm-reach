# Setup

1. Follow the detailed [credential and first-run guide](credentials.md).
2. Copy `.env.example` to `.env` and enter the local values from that guide.
3. Start the stack:

```powershell
docker compose up -d
```

4. Open n8n at `http://localhost:5678` and create the initial owner account.
5. Import the workflow exports from `n8n/workflows`.
6. Configure Gmail OAuth and SMTP credentials in the n8n UI.
7. Pull local models in Ollama:

```powershell
docker compose exec ollama ollama pull qwen3:4b
docker compose exec ollama ollama pull nomic-embed-text
```

8. Open the built-in dashboard at `http://localhost:8087/dashboard`. It is available whenever the worker is running.

9. Optional Appsmith dashboard:

```powershell
docker compose --profile dashboard up -d appsmith
```
