# Security Model

## Identity

Users authenticate with email/password and receive an HS256 JWT. Passwords are
hashed with Passlib bcrypt. `RAG_API_SECRET_KEY` must be unique per environment
and rotated if exposed.

## Roles

- `admin`: full document visibility, user administration, public publishing.
- `manager`: can publish public documents and access own/team/public documents.
- `employee`: can upload private/team documents and access own/team/public
  documents.

## Document Visibility

Authorization is enforced in the repository layer. The RAG flow intentionally
checks every Qdrant candidate against Postgres before it becomes prompt context.

Visibility rules:

- `private`: owner or admin.
- `team`: same team or admin.
- `public`: any authenticated user.

## Operational Controls

- Do not expose Qdrant directly on the public internet.
- Keep `.env` out of git.
- Use TLS and a managed secret store in production.
- Add audit logs before handling regulated data.
- Add virus scanning and file-size limits before accepting untrusted uploads at
  scale.
