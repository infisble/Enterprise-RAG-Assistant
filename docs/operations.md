# Operations

## Local Stack

```bash
docker compose up --build
```

Services:

- `postgres`: metadata and users.
- `qdrant`: vector index.
- `backend`: FastAPI and Alembic migrations.
- `frontend`: nginx-served React build.

## Migrations

The backend container runs `alembic upgrade head` at startup. For manual
migration work:

```bash
cd backend
alembic revision --autogenerate -m "change description"
alembic upgrade head
```

## Provider Modes

`mock`
: No network LLM calls. Good for smoke tests and UI demos.

`openai`
: Requires `OPENAI_API_KEY`; uses configured chat and embedding models.

`gemini`
: Requires `GEMINI_API_KEY`; uses configured generateContent and embedding
models.

## Scaling Notes

- Move upload parsing and embedding to a queue when files become large.
- Store raw files in object storage rather than Postgres.
- Add per-tenant Qdrant collections or payload filters for multi-tenant SaaS.
- Add observability around upload duration, embedding latency, retrieval hit rate,
  and answer latency.
