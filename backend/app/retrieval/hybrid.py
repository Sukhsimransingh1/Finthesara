from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.schemas import (
    EvidenceItem,
    EvidencePackage,
    FusedSearchResponse,
    RetrievalFilters,
)
from app.retrieval.sparse_store import SparseRetriever
from app.retrieval.vector_store import VectorRetriever


class EvidencePackageBuilder:
    """Build a traceable evidence package from fused retrieval results."""

    def build(
        self,
        fused_response: FusedSearchResponse,
        *,
        project_id: UUID,
        filters: RetrievalFilters | None = None,
    ) -> EvidencePackage:
        evidence: list[EvidenceItem] = []

        for result in fused_response.results:
            metadata = result.metadata

            page_number = metadata.get("page_number")
            parsed_page_number: int | None = None

            if page_number is not None:
                try:
                    parsed_page_number = int(str(page_number))
                except ValueError:
                    parsed_page_number = None

            company = metadata.get("company")
            document_type = metadata.get("document_type")
            publication_date = metadata.get("publication_date")
            source_url = metadata.get("source_url")

            retrieval_methods: list[str] = []

            if result.vector_rank is not None:
                retrieval_methods.append("vector")

            if result.sparse_rank is not None:
                retrieval_methods.append("sparse")

            evidence.append(
                EvidenceItem(
                    evidence_id=str(uuid4()),
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    content=result.content,
                    company=(
                        str(company)
                        if company is not None
                        else None
                    ),
                    document_type=(
                        str(document_type)
                        if document_type is not None
                        else None
                    ),
                    publication_date=self._parse_date(
                        publication_date
                    ),
                    page_number=parsed_page_number,
                    source_url=(
                        str(source_url)
                        if source_url is not None
                        else None
                    ),
                    vector_rank=result.vector_rank,
                    sparse_rank=result.sparse_rank,
                    vector_score=result.vector_score,
                    sparse_score=result.sparse_score,
                    rrf_score=result.rrf_score,
                    retrieval_methods=retrieval_methods,
                )
            )

        return EvidencePackage(
            query=fused_response.query,
            project_id=project_id,
            filters=filters,
            evidence=evidence,
            evidence_count=len(evidence),
            retrieval_config={
                "fusion": "weighted_rrf",
                "rrf_k": 60,
                "vector_weight": 1.0,
                "sparse_weight": 1.0,
            },
        )

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if value is None:
            return None

        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None


class HybridRetriever:
    """Combine vector and sparse retrieval into a traceable evidence package."""

    def __init__(
        self,
        *,
        vector_retriever: VectorRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        evidence_builder: EvidencePackageBuilder | None = None,
    ) -> None:
        self.vector_retriever = (
            vector_retriever
            or VectorRetriever()
        )

        self.sparse_retriever = (
            sparse_retriever
            or SparseRetriever()
        )

        self.evidence_builder = (
            evidence_builder
            or EvidencePackageBuilder()
        )

    def search(
        self,
        query: str,
        *,
        project_id: UUID,
        top_k: int = 10,
        retrieval_k: int = 20,
        similarity_threshold: float = 0.0,
        filters: RetrievalFilters | None = None,
    ) -> EvidencePackage:
        if not query.strip():
            raise ValueError(
                "Hybrid search query cannot be empty."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than or equal to 1."
            )

        if top_k > 100:
            raise ValueError(
                "top_k cannot exceed 100."
            )

        if retrieval_k < top_k:
            raise ValueError(
                "retrieval_k must be greater than or equal to top_k."
            )

        if retrieval_k > 100:
            raise ValueError(
                "retrieval_k cannot exceed 100."
            )

        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0."
            )

        if filters is not None:
            filters.validate_range()

        vector_response = self.vector_retriever.search(
            query,
            project_id=project_id,
            top_k=retrieval_k,
            similarity_threshold=similarity_threshold,
            filters=filters,
        )

        sparse_response = self.sparse_retriever.search(
            query,
            project_id=project_id,
            top_k=retrieval_k,
            filters=filters,
        )

        fused_response = reciprocal_rank_fusion(
            vector_response,
            sparse_response,
            top_k=top_k,
        )

        evidence_package = self.evidence_builder.build(
            fused_response,
            project_id=project_id,
            filters=filters,
        )

        return evidence_package
