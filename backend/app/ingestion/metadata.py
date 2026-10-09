from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.schemas.ingestion import DocumentMetadata


class MetadataExtractor:
    """Extract deterministic metadata from a document path and filename."""

    _DATE_PATTERNS = (
        re.compile(r"(?P<year>20\d{2})[-_](?P<month>\d{2})[-_](?P<day>\d{2})"),
        re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})"),
    )

    def extract(
        self,
        file_path: str | Path,
        *,
        document_type: str = "unknown",
        company: str | None = None,
        source_url: str | None = None,
    ) -> DocumentMetadata:
        path = Path(file_path)

        return DocumentMetadata(
            filename=path.name,
            file_path=str(path),
            document_type=document_type,
            company=company,
            publication_date=self._extract_date(path.name),
            source_url=source_url,
        )

    def _extract_date(self, filename: str) -> date | None:
        for pattern in self._DATE_PATTERNS:
            match = pattern.search(filename)

            if not match:
                continue

            try:
                return date(
                    int(match.group("year")),
                    int(match.group("month")),
                    int(match.group("day")),
                )
            except ValueError:
                return None

        return None