from pathlib import Path

import fitz
import pytest
from app.ingestion.parser import DocumentParseError, PDFParser


def create_test_pdf(path: Path) -> None:
    """Create a small PDF for parser tests."""

    document = fitz.open()

    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Page one content.",
    )

    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Page two content.",
    )

    document.save(path)
    document.close()


def test_parser_preserves_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    create_test_pdf(pdf_path)

    result = PDFParser().parse(pdf_path)

    assert result.page_count == 2
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert "Page one content." in result.pages[0].text
    assert "Page two content." in result.pages[1].text


def test_parser_rejects_missing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.pdf"

    with pytest.raises(DocumentParseError, match="does not exist"):
        PDFParser().parse(missing_file)


def test_parser_rejects_non_pdf_file(tmp_path: Path) -> None:
    text_file = tmp_path / "document.txt"
    text_file.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(
        DocumentParseError,
        match=r"Unsupported document type: \.txt",
    ):
        PDFParser().parse(text_file)