# agentic-finance-research backend

This directory contains the Phase 0 backend foundation for `agentic-finance-research`. It exposes only a versioned health endpoint and configuration/logging infrastructure. Agents, LangGraph workflows, retrieval, ingestion, embeddings, financial tools, verification, and evaluations are intentionally not implemented yet.

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
