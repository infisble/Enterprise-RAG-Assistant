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
hybrid retrieval, visibility filtering, reranking, grounding, prompt construction
through `LLMService`, chat history, and response assembly; `AuthService` owns
bootstrap registration and JWT issuance.

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
- `chat_sessions`: conversation containers for memory and history.
- `chat_messages`: user/assistant turns with citations and latency.
- `llm_requests`: prompt/response logs, token usage, cost, status, errors.
- `feedback`: user feedback placeholder for answer quality.
- `audit_logs`: user, document, and chat events tied to request ids.

Qdrant stores vectors and lightweight payload metadata, but authorization is
verified against Postgres before citations reach the LLM.

## Retrieval Path

1. Embed the question.
2. Search Qdrant for candidate chunk IDs.
3. Search visible PostgreSQL chunks with keyword matching.
4. Apply metadata filters such as `document_id`, `team_id`, and `visibility`.
5. Load each vector candidate through `DocumentRepository.get_visible_chunk`.
6. Drop chunks outside the current user's visibility scope.
7. Rerank by a weighted vector/keyword score.
8. Run grounding checks before generation.
9. Send only authorized chunks to the LLM prompt.
10. Return answer plus citations, or the fallback when context is insufficient.

This means vector search can over-retrieve, but unauthorized text is never used
for answer generation.

## Grounding

The assistant answers only from supplied context. If retrieved chunks do not
overlap enough with the question, or if a real provider returns an answer without
source markers, the backend returns:

```text
I don't know based on provided documents.
```

Grounding failures are stored in `llm_requests.status` and surface in dashboard
failed-answer metrics.

## Observability

Every HTTP request receives an `x-request-id`. Backend logs are structured JSON
and include request id, method, path, status code, and latency. Chat calls store
prompt, response, token usage, estimated cost, provider, status, errors, and
latency in `llm_requests`. User/document/chat actions are persisted in
`audit_logs`.

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
