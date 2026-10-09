from __future__ import annotations

from pathlib import Path

from app.ingestion.chunker import DocumentChunker
from app.ingestion.cleaner import TextCleaner
from app.ingestion.metadata import MetadataExtractor
from app.ingestion.parser import ParsedPage, PDFParser
from app.schemas.ingestion import (
    IngestedChunk,
    IngestedPage,
    IngestionResult,
)


class DocumentIngestionService:
    """Orchestrate the deterministic document ingestion pipeline."""

    def __init__(
        self,
        *,
        parser: PDFParser | None = None,
        cleaner: TextCleaner | None = None,
        metadata_extractor: MetadataExtractor | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self.parser = parser or PDFParser()
        self.cleaner = cleaner or TextCleaner()
        self.metadata_extractor = (
            metadata_extractor or MetadataExtractor()
        )
        self.chunker = chunker or DocumentChunker()

    def ingest(
        self,
        file_path: str | Path,
        *,
        document_type: str = "unknown",
        company: str | None = None,
        source_url: str | None = None,
    ) -> IngestionResult:
        """Parse, clean, enrich, and chunk a document."""

        parsed_document = self.parser.parse(file_path)

        cleaned_pages = [
            ParsedPage(
                page_number=page.page_number,
                text=self.cleaner.clean(page.text),
            )
            for page in parsed_document.pages
        ]

        metadata = self.metadata_extractor.extract(
            file_path,
            document_type=document_type,
            company=company,
            source_url=source_url,
        )

        chunks = self.chunker.chunk(cleaned_pages)

        ingested_pages = [
            IngestedPage(
                page_number=page.page_number,
                text=page.text,
            )
            for page in cleaned_pages
        ]

        ingested_chunks = [
            IngestedChunk(
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                page_number=chunk.page_number,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
            for chunk in chunks
        ]

        return IngestionResult(
            metadata=metadata,
            pages=ingested_pages,
            chunks=ingested_chunks,
        )