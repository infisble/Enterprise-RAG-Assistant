# Architecture

Enterprise RAG Assistant uses a layered backend and a small operational frontend.
The backend owns all access control decisions; the frontend only presents the
current user's allowed data.

## Backend Layers

`api`
: FastAPI routers, request dependencies, and HTTP status handling. Routers should
stay thin and delegate orchestration to services.

`schemas`
: Pydantic contracts for external API payloads. These are the only shapes the UI
and API clients should rely on.

`services`
: Business workflows. `DocumentService` owns ingestion; `RagService` owns
retrieval, visibility filtering, prompt construction through `LLMService`, and
response assembly; `AuthService` owns bootstrap registration and JWT issuance.

`repositories`
: SQLAlchemy query composition and persistence. This layer centralizes visibility
queries so RBAC is not duplicated across routes.

`db`
: SQLAlchemy models and session construction. Postgres is the source of truth for
users, teams, document metadata, and chunk records.

`core`
: Cross-cutting concerns such as settings, logging, and JWT/password security.

## Data Model

- `teams`: business unit boundary such as HR or Finance.
- `users`: login identity, role, active flag, optional team.
- `documents`: title, filename, owner, team, and visibility.
- `document_chunks`: extracted text chunks and Qdrant point IDs.

Qdrant stores vectors and lightweight payload metadata, but authorization is
verified against Postgres before citations reach the LLM.

## Retrieval Path

1. Embed the question.
2. Search Qdrant for candidate chunk IDs.
3. Load each candidate through `DocumentRepository.get_visible_chunk`.
4. Drop chunks outside the current user's visibility scope.
5. Send only authorized chunks to the LLM prompt.
6. Return answer plus citations.

This means vector search can over-retrieve, but unauthorized text is never used
for answer generation.

## Provider Strategy

`RAG_LLM_PROVIDER` selects `mock`, `openai`, or `gemini`.

- `mock` uses deterministic local embeddings and a local placeholder answer.
- `openai` uses OpenAI embeddings and chat completions.
- `gemini` uses Gemini embeddings and `generateContent`.

Embedding vectors are normalized to `RAG_EMBEDDING_DIM` so the local collection
dimension remains predictable.

## Extension Points

- Add queued ingestion under `app/workers` for large files.
- Add object storage for raw file retention.
- Add audit-log tables for enterprise compliance.
- Add streaming chat by extending `LLMService` and the `/api/chat` route.
