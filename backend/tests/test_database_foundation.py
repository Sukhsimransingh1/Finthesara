"""Tests for the migration and explicit database-access foundations."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.config import Settings
from app.db.connection import create_database
from app.schemas.database import DocumentChunkRecord
from pydantic import SecretStr, ValidationError

MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"


def test_database_is_not_constructed_without_configuration() -> None:
    assert create_database(Settings(database_url=None)) is None


def test_database_engine_construction_does_not_require_a_connection() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql+asyncpg://postgres:password@db.example.test:5432/postgres"
        )
    )

    database = create_database(settings)

    assert database is not None
    assert database.engine.url.get_backend_name() == "postgresql"


def test_migrations_are_ordered_and_include_all_required_entities() -> None:
    migration_names = [path.name for path in sorted(MIGRATIONS_DIRECTORY.glob("*.sql"))]
    assert migration_names == [
    "001_initial_schema.sql",
    "002_indexes.sql",
    "003_rls.sql",
    "004_vector_embeddings.sql",
    "005_vector_search.sql",
    "006_sparse_search.sql",
    "007_retrieval_metadata.sql",
]
    initial_schema = (MIGRATIONS_DIRECTORY / "001_initial_schema.sql").read_text(encoding="utf-8")
    required_tables = {
        "profiles",
        "projects",
        "research_runs",
        "research_tasks",
        "documents",
        "document_chunks",
        "sources",
        "claims",
        "claim_evidence",
        "calculations",
        "verification_results",
        "human_reviews",
        "evaluation_datasets",
        "evaluation_cases",
        "evaluation_runs",
        "feedback",
    }
    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS public.{table}" in initial_schema


def test_schema_captures_pgvector_and_traceable_claim_evidence_constraints() -> None:
    initial_schema = (MIGRATIONS_DIRECTORY / "001_initial_schema.sql").read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector;" in initial_schema
    assert "embedding vector," in initial_schema
    assert "REFERENCES public.document_chunks (id) ON DELETE SET NULL" in initial_schema
    assert "REFERENCES public.calculations (id) ON DELETE SET NULL" in initial_schema
    assert "CONSTRAINT claim_evidence_has_evidence CHECK" in initial_schema


def test_rls_migration_enables_ownership_policies_without_open_access() -> None:
    rls_migration = (MIGRATIONS_DIRECTORY / "003_rls.sql").read_text(encoding="utf-8")

    assert "ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;" in rls_migration
    assert "ALTER TABLE public.research_runs ENABLE ROW LEVEL SECURITY;" in rls_migration
    assert "ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;" in rls_migration
    assert "auth.uid()" in rls_migration
    assert "USING (true)" not in rls_migration


def test_document_chunk_record_rejects_a_negative_chunk_index() -> None:
    with pytest.raises(ValidationError):
        DocumentChunkRecord(
            id=uuid4(),
            created_at=datetime.now(UTC),
            document_id=uuid4(),
            chunk_index=-1,
            content="A valid chunk.",
        )
