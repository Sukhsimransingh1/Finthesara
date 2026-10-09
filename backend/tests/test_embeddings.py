from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest
from app.retrieval.embeddings import (
    EXPECTED_DIMENSION,
    EmbeddingService,
)


def test_embedding_dimension() -> None:
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 768

    service = EmbeddingService(model=model)

    assert service.dimension == 768


def test_wrong_model_dimension_is_rejected() -> None:
    model = Mock()
    model.get_sentence_embedding_dimension.return_value = 1536

    service = EmbeddingService(model=model)

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        service.embed_text("Revenue increased by 10%.")


def test_empty_text_is_rejected() -> None:
    model = Mock()

    service = EmbeddingService(model=model)

    with pytest.raises(ValueError, match="empty text"):
        service.embed_text("   ")


def test_empty_document_list_is_rejected() -> None:
    model = Mock()

    service = EmbeddingService(model=model)

    with pytest.raises(
        ValueError,
        match="empty document list",
    ):
        service.embed_documents([])


def test_empty_document_text_is_rejected() -> None:
    model = Mock()

    service = EmbeddingService(model=model)

    with pytest.raises(
        ValueError,
        match="empty strings",
    ):
        service.embed_documents(
            ["Revenue increased.", "   "]
        )


def test_batch_embedding_returns_expected_count() -> None:
    model = Mock()

    model.get_sentence_embedding_dimension.return_value = (
        EXPECTED_DIMENSION
    )

    model.encode.return_value = np.array(
    [
        [0.1] * EXPECTED_DIMENSION,
        [0.2] * EXPECTED_DIMENSION,
    ]
)

    service = EmbeddingService(model=model)

    result = service.embed_documents(
        [
            "Revenue increased.",
            "Operating margin improved.",
        ]
    )

    assert len(result.embeddings) == 2
    assert result.dimension == EXPECTED_DIMENSION
    assert len(result.embeddings[0]) == EXPECTED_DIMENSION
    assert len(result.embeddings[1]) == EXPECTED_DIMENSION


def test_batch_embedding_preserves_input_count() -> None:
    model = Mock()

    model.get_sentence_embedding_dimension.return_value = (
        EXPECTED_DIMENSION
    )

    model.encode.return_value = np.array(
    [
        [0.1] * EXPECTED_DIMENSION,
    ]
)

    service = EmbeddingService(model=model)

    result = service.embed_documents(
        ["Revenue increased."]
    )

    assert len(result.embeddings) == 1