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
  "top_k": 5
}
```

Returns:

```json
{
  "answer": "string",
  "provider": "mock",
  "citations": [
    {
      "document_id": 1,
      "document_title": "Employee Handbook",
      "chunk_id": 10,
      "chunk_index": 0,
      "score": 0.91,
      "text": "source text"
    }
  ]
}
```
