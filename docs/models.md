# Models

Default local runtime: Ollama.

Configurable environment variables:

- `OLLAMA_CHAT_MODEL`
- `OLLAMA_EMBEDDING_MODEL`
- `OLLAMA_BASE_URL`

Suggested chat model order from the prompt:

1. Qwen 3
2. DeepSeek
3. Llama 3
4. Gemma

Suggested embedding models:

- `nomic-embed-text`
- `bge-small-en`
- `all-MiniLM-L6-v2`

The worker accepts model names from environment variables so the workflow can change models without code edits.

