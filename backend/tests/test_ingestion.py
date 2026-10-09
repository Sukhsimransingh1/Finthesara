from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import fitz
import pytest
from app.ingestion.cleaner import TextCleaner
from app.ingestion.metadata import MetadataExtractor
from app.services.document_service import DocumentIngestionService


def create_integration_pdf(path: Path) -> None:
    """Create a deterministic two-page PDF for integration tests."""

    document = fitz.open()

    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Revenue   increased by 14.2%.\n\n\n"
        "Operating margin was 18.7%.",
    )

    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Free cash flow increased by 11.3%.",
    )

    document.save(path)
    document.close()


def test_cleaner_normalizes_whitespace() -> None:
    cleaner = TextCleaner()

    text = "Revenue   increased.\r\n\r\n\r\nMargin was 18.7%."

    cleaned = cleaner.clean(text)

    assert cleaned == (
        "Revenue increased.\n\n"
        "Margin was 18.7%."
    )


def test_cleaner_preserves_financial_values() -> None:
    cleaner = TextCleaner()

    text = "Revenue increased by 14.2% and margin was 18.7%."

    cleaned = cleaner.clean(text)

    assert "14.2%" in cleaned
    assert "18.7%" in cleaned


def test_cleaner_handles_unicode() -> None:
    cleaner = TextCleaner()

    text = "Café — Revenue increased by €1,200."

    cleaned = cleaner.clean(text)

    assert "Café" in cleaned
    assert "€1,200" in cleaned


def test_cleaner_handles_empty_text() -> None:
    assert TextCleaner().clean("") == ""


def test_cleaner_handles_whitespace_only_text() -> None:
    assert TextCleaner().clean("   \n\n   ") == ""


def test_metadata_extraction() -> None:
    extractor = MetadataExtractor()

    result = extractor.extract(
        "apple_2025-10-31_10k.pdf",
        document_type="10-K",
        company="Apple",
        source_url="https://example.com/report.pdf",
    )

    assert result.filename == "apple_2025-10-31_10k.pdf"
    assert result.document_type == "10-K"
    assert result.company == "Apple"
    assert result.source_url == "https://example.com/report.pdf"
    assert result.publication_date == date(2025, 10, 31)


def test_metadata_extracts_compact_date() -> None:
    extractor = MetadataExtractor()

    result = extractor.extract(
        "company_20250930_report.pdf",
    )

    assert result.publication_date == date(2025, 9, 30)


def test_metadata_handles_missing_date() -> None:
    extractor = MetadataExtractor()

    result = extractor.extract(
        "company_annual_report.pdf",
    )

    assert result.publication_date is None


def test_metadata_handles_invalid_date() -> None:
    extractor = MetadataExtractor()

    result = extractor.extract(
        "company_2025-99-99_report.pdf",
    )

    assert result.publication_date is None


def test_metadata_extractor_rejects_unexpected_field() -> None:
    extractor = MetadataExtractor()

    invalid_kwargs: dict[str, Any] = {
        "unexpected_field": "should fail",
    }

    with pytest.raises(TypeError):
        extractor.extract(
            "company_annual_report.pdf",
            document_type="annual_report",
            company="Acme Corp",
            source_url=None,
            **invalid_kwargs,
        )


def test_document_ingestion_pipeline(tmp_path: Path) -> None:
    pdf_path = tmp_path / "apple_2025-10-31_10k.pdf"

    create_integration_pdf(pdf_path)

    result = DocumentIngestionService().ingest(
        pdf_path,
        document_type="10-K",
        company="Apple",
        source_url="https://example.com/report.pdf",
    )

    assert result.metadata.filename == (
        "apple_2025-10-31_10k.pdf"
    )
    assert result.metadata.document_type == "10-K"
    assert result.metadata.company == "Apple"
    assert result.page_count == 2
    assert result.chunk_count >= 2

    assert "Revenue increased by 14.2%." in (
        result.pages[0].text
    )
    assert "18.7%" in result.pages[0].text

    assert any(
        "14.2%" in chunk.text
        for chunk in result.chunks
    )

    assert any(
        "11.3%" in chunk.text
        for chunk in result.chunks
    )


def test_document_ingestion_rejects_missing_file(
    tmp_path: Path,
) -> None:
    service = DocumentIngestionService()

    missing_file = tmp_path / "missing.pdf"

    try:
        service.ingest(missing_file)
    except Exception as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError(
            "Missing file was unexpectedly accepted"
        )