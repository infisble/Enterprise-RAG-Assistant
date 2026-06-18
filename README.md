# Enterprise RAG Assistant

Enterprise RAG Assistant is a full-stack reference implementation for secure
document question answering. It accepts PDF, DOCX, and TXT files, chunks and
embeds the extracted text, stores vectors in Qdrant, persists metadata and access
rules in PostgreSQL, and answers chat questions with source citations.

The code is intentionally structured like a production service rather than a
single-file demo: FastAPI routes are thin, business logic lives in services,
database access lives in repositories, and configuration is environment-driven.

## Capabilities

- FastAPI backend with typed Pydantic request/response schemas.
- PostgreSQL metadata store with Alembic migrations.
- Qdrant vector database for semantic retrieval.
- OpenAI and Gemini provider adapters, plus a local mock mode for development.
- PDF, DOCX, and TXT ingestion.
- Text chunking with overlap and deterministic fallback embeddings.
- `/api/chat` endpoint returning an answer and citations.
- Hybrid retrieval with vector search, keyword search, metadata filtering, and reranking.
- Grounding guard and fixed fallback: `I don't know based on provided documents.`
- Conversation memory and persisted chat history.
- JWT authentication with `admin`, `manager`, and `employee` roles.
- Document visibility: `private`, `team`, and `public`.
- React/Vite admin console for login, dashboard, documents, upload, chat, history, users, logs, and metrics.
- Structured logs, request ids, latency tracking, token usage, cost tracking, prompt/response logs, and audit logs.
- Docker Compose for the full local stack.

## Architecture

```text
backend/
  app/
    api/            FastAPI routers and dependencies
    core/           config, logging, security
    db/             SQLAlchemy engine and ORM models
    repositories/   persistence queries and access scopes
    schemas/        Pydantic API contracts
    services/       ingestion, embeddings, vector search, RAG, auth
    workers/        reserved for async ingestion extensions
    tests/          unit tests for pure logic and access rules
  migrations/       Alembic migration history
frontend/
  src/              React console
docs/               architecture, API, security, operations
docker-compose.yml  Postgres, Qdrant, backend, frontend
```

High-level flow:

```mermaid
sequenceDiagram
  actor User
  participant UI as React UI
  participant API as FastAPI
  participant PG as PostgreSQL
  participant Q as Qdrant
  participant LLM as OpenAI/Gemini

  User->>UI: Upload PDF/DOCX/TXT
  UI->>API: POST /api/documents
  API->>API: Parse and chunk text
  API->>LLM: Create embeddings
  API->>PG: Save document/chunk metadata and visibility
  API->>Q: Upsert vectors
  User->>UI: Ask question
  UI->>API: POST /api/chat
  API->>Q: Vector search
  API->>PG: Keyword search and RBAC filtering
  API->>API: Rerank and grounding guard
  API->>LLM: Answer from retrieved context
  API-->>UI: Answer with citations
```

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- Backend OpenAPI: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/api/health`
- Qdrant dashboard/API: `http://localhost:6333/dashboard`

The default `RAG_LLM_PROVIDER=mock` works without cloud credentials. Configure
OpenAI or Gemini in `.env` when you want production LLM responses and provider
embeddings.

## First User Bootstrap

The first registered user becomes `admin`. Later users are created as
`employee`. Admins can update users through:

```http
PATCH /api/auth/users/{user_id}
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "role": "manager",
  "team_name": "Finance"
}
```

## API Overview

### Register

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "ChangeMe123!",
  "full_name": "Admin User",
  "team_name": "HR"
}
```

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "ChangeMe123!"
}
```

### Upload Document

```http
POST /api/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<pdf/docx/txt>
title=Employee Handbook
visibility=team
team_id=1
```

### Chat

```http
POST /api/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "What is the vacation policy?",
  "top_k": 5,
  "metadata_filter": {
    "visibility": "team"
  }
}
```

Response:

```json
{
  "session_id": 1,
  "message_id": 2,
  "answer": "Employees can request vacation according to the policy [1].",
  "provider": "openai",
  "grounded": true,
  "latency_ms": 420,
  "estimated_cost_usd": 0.0001,
  "citations": [
    {
      "document_id": 1,
      "document_title": "Employee Handbook",
      "chunk_id": 12,
      "chunk_index": 3,
      "score": 0.82,
      "text": "..."
    }
  ]
}
```

If the accessible documents do not support the question, the API returns:

```text
I don't know based on provided documents.
```

## Visibility Model

- `private`: visible only to the document owner and admins.
- `team`: visible to users in the same team and admins.
- `public`: visible to all authenticated users.

Employees may upload private/team documents. Publishing public documents is
restricted to managers and admins.

## Configuration

Important environment variables:

```env
RAG_API_SECRET_KEY=replace-with-a-long-random-secret
RAG_DATABASE_URL=postgresql+psycopg2://rag:rag@postgres:5432/rag
RAG_QDRANT_URL=http://qdrant:6333
RAG_LLM_PROVIDER=mock
OPENAI_API_KEY=
GEMINI_API_KEY=
```

See [.env.example](.env.example) for the complete configuration surface.

## Development

Backend:

```bash
cd backend
pip install -r requirements.txt
pytest app/tests
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

Database migrations:

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Production Notes

- Replace `RAG_API_SECRET_KEY` before deployment.
- Use managed Postgres with backups and point-in-time recovery.
- Protect Qdrant with network policy or API keys; do not expose it publicly.
- Keep `.env` out of git and rotate any leaked provider credentials.
- For large deployments, move ingestion to `backend/app/workers` with a queue.
- Add object storage for raw files if retention is required.
- Add audit logs for admin role changes and document reads.

More details are in [docs/architecture.md](docs/architecture.md),
[docs/api.md](docs/api.md), and [docs/security.md](docs/security.md).
