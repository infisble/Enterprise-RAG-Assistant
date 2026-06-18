# API Reference

Base URL: `http://localhost:8000/api`

All endpoints except `GET /health`, `POST /auth/register`, and `POST /auth/login`
require `Authorization: Bearer <token>`.

## Auth

`POST /auth/register`
: Creates a user. The first registered user is promoted to `admin`; later users
default to `employee`.

`POST /auth/login`
: Returns a JWT bearer token.

`GET /auth/me`
: Returns the current user.

`GET /auth/users`
: Admin-only user list.

`PATCH /auth/users/{user_id}`
: Admin-only role/team update.

Allowed roles are `admin`, `manager`, and `employee`.

## Documents

`POST /documents`
: Multipart upload. Supported extensions are `.pdf`, `.docx`, and `.txt`.

Fields:

- `file`: required upload.
- `title`: optional display title.
- `visibility`: `private`, `team`, or `public`.
- `team_id`: optional explicit team target.

`GET /documents`
: Lists documents visible to the current user.

## Chat

`POST /chat`

```json
{
  "question": "What is the vacation policy?",
  "top_k": 5,
  "session_id": 12,
  "metadata_filter": {
    "visibility": "team",
    "team_id": 1
  }
}
```

Returns:

```json
{
  "session_id": 12,
  "message_id": 44,
  "answer": "string",
  "provider": "mock",
  "grounded": true,
  "latency_ms": 120,
  "estimated_cost_usd": 0.0,
  "citations": [
    {
      "document_id": 1,
      "document_title": "Employee Handbook",
      "chunk_id": 10,
      "chunk_index": 0,
      "score": 0.91,
      "vector_score": 0.88,
      "keyword_score": 1.0,
      "text": "source text"
    }
  ]
}
```

`GET /chat/history`
: Returns the current user's chat sessions, messages, latency, and citations.

## Admin

`GET /admin/metrics`
: Manager/admin dashboard metrics: documents, chunks, queries, average latency,
estimated cost, top questions, and failed answers.

`GET /admin/llm-requests`
: Manager/admin prompt-response observability records with token and cost data.

`GET /admin/audit-logs`
: Manager/admin audit events for uploads, user updates, and chat calls.
