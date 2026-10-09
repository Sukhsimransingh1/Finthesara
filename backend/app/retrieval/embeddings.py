from __future__ import annotations

from functools import lru_cache
from typing import cast

from sentence_transformers import SentenceTransformer

from app.retrieval.schemas import BatchEmbeddingResult, EmbeddingResult

MODEL_NAME = "BAAI/bge-base-en-v1.5"
EXPECTED_DIMENSION = 768


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once per backend process."""
    model = SentenceTransformer(MODEL_NAME)
    return cast(SentenceTransformer, model)


class EmbeddingService:
    """Generate semantic embeddings for financial research documents."""

    def __init__(self, model: SentenceTransformer | None = None) -> None:
        self.model = model or get_embedding_model()

    @property
    def dimension(self) -> int:
        dimension = self.model.get_sentence_embedding_dimension()

        if dimension is None:
            raise RuntimeError(
                "The embedding model did not provide a fixed dimension."
            )

        return int(dimension)

    def _validate_dimension(self, dimension: int) -> None:
        if dimension != EXPECTED_DIMENSION:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected "
                f"{EXPECTED_DIMENSION}, got {dimension}."
            )

    def embed_text(self, text: str) -> EmbeddingResult:
        if not text.strip():
            raise ValueError("Cannot embed empty text.")

        dimension = self.dimension
        self._validate_dimension(dimension)

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        ).tolist()

        embedding = [float(value) for value in vector]

        if len(embedding) != EXPECTED_DIMENSION:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected "
                f"{EXPECTED_DIMENSION}, got {len(embedding)}."
            )

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            dimension=len(embedding),
        )

    def embed_documents(self, texts: list[str]) -> BatchEmbeddingResult:
        if not texts:
            raise ValueError("Cannot embed an empty document list.")

        if any(not text.strip() for text in texts):
            raise ValueError("Document texts cannot contain empty strings.")

        dimension = self.dimension
        self._validate_dimension(dimension)

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        ).tolist()

        embeddings = [
            [float(value) for value in vector]
            for vector in vectors
        ]

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "The embedding model returned a different number "
                "of embeddings than input documents."
            )

        if not embeddings:
            raise RuntimeError(
                "The embedding model returned no embeddings."
            )

        if any(len(vector) != EXPECTED_DIMENSION for vector in embeddings):
            raise RuntimeError(
                f"One or more embeddings do not have the expected "
                f"{EXPECTED_DIMENSION} dimensions."
            )

        return BatchEmbeddingResult(
            embeddings=embeddings,
            dimension=EXPECTED_DIMENSION,
        )