# agentic-finance-research backend

This directory contains the Phase 0 and Phase 1 backend foundations for `agentic-finance-research`. It exposes only a versioned health endpoint, configuration/logging infrastructure, and a database schema/migration foundation. Agents, LangGraph workflows, retrieval, ingestion, embedding generation, financial tools, verification, and evaluation execution are intentionally not implemented yet.

## Requirements

- Python 3.12
- Docker (optional)

## Local setup

From the repository root:

```powershell
cd backend
Copy-Item .env.example .env
uv sync --python 3.12 --all-groups
uv run uvicorn app.main:app --reload
```

The service is available at `http://127.0.0.1:8000`. Check `GET /api/v1/health`; FastAPI documentation is at `/docs`.

Populate only the environment variables required for the capabilities you enable. Do not commit `.env`, API keys, Supabase service-role credentials, or database passwords.

## Database foundation

Supabase PostgreSQL is the primary persistence layer. The ordered SQL migrations in `migrations/` create the relational schema, indexes, and Row-Level Security policies:

1. `001_initial_schema.sql` creates `pgcrypto`, `vector`, tables, constraints, and timestamp triggers.
2. `002_indexes.sql` adds indexes for ownership, lifecycle status, provenance, and future metadata filtering.
3. `003_rls.sql` enables ownership-based RLS using Supabase `auth.uid()`.

Apply these files in numerical order using the Supabase SQL Editor or your deployment migration runner. They target a fresh Supabase project, where `auth.users` already exists:

```sql
-- Run each migration file in order: 001, then 002, then 003.
```

Set `DATABASE_URL` to Supabase's direct async PostgreSQL connection string and retain `EMBEDDING_DIMENSION` as the single provider-dimension setting. `document_chunks.embedding` is pgvector-ready but intentionally has no ANN index or embedding writer until a later retrieval phase fixes the embedding provider and query metric.

RLS grants a signed-in user access only to their profile and project-owned data, including records reached through runs, documents, claims, and evidence. Evaluation datasets are owner-scoped. A Supabase service-role key bypasses RLS; it is only for trusted server-side operations and must never reach a browser or be logged.

`app.db.connection.create_database()` constructs an async SQLAlchemy engine explicitly and never connects during import or FastAPI startup. Repository implementations remain deferred until a feature needs them.

## Quality checks

```powershell
uv run pytest
uv run ruff check app tests
uv run mypy app tests
```

## Docker

```powershell
cd backend
docker build -t agentic-finance-research-backend .
docker run --rm -p 8000:8000 --env-file .env agentic-finance-research-backend
```

## Current layout

`app/api/v1` contains versioned routes. `app/core` owns cross-cutting logging. `app/db` owns PostgreSQL/Supabase configuration only; it does not open a database connection yet. `app/schemas` contains typed API contracts. The remaining domain packages are intentionally empty boundaries reserved for later approved phases.
