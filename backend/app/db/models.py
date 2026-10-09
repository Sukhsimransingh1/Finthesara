"""Database model boundary.

The SQL migrations in ``backend/migrations`` are canonical for relational
schema. Pydantic record schemas are intentionally kept separate in
``app.schemas.database`` so database rows never become public API contracts.
"""

from app.schemas.database import (
    CalculationRecord,
    ClaimRecord,
    DocumentChunkRecord,
    DocumentRecord,
    ProjectRecord,
    ResearchRunRecord,
    ResearchTaskRecord,
    SourceRecord,
    VerificationResultRecord,
)

__all__ = [
    "CalculationRecord",
    "ClaimRecord",
    "DocumentChunkRecord",
    "DocumentRecord",
    "ProjectRecord",
    "ResearchRunRecord",
    "ResearchTaskRecord",
    "SourceRecord",
    "VerificationResultRecord",
]
