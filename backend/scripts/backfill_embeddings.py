from __future__ import annotations

from typing import Any

from app.db.supabase_client import get_supabase_client
from app.retrieval.embeddings import EmbeddingService

EXPECTED_DIMENSION = 768


def _row_as_dict(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise RuntimeError("Supabase returned an unexpected row format.")
    return row


def main() -> None:
    client = get_supabase_client()
    embedding_service = EmbeddingService()

    response = (
        client.table("document_chunks")
        .select("id, content")
        .is_("embedding", "null")
        .execute()
    )

    rows = [_row_as_dict(row) for row in (response.data or [])]

    if not rows:
        print("No chunks require embedding.")
        return

    print(f"Found {len(rows)} chunks without embeddings.")

    texts = [str(row["content"]) for row in rows]
    embedding_result = embedding_service.embed_documents(texts)

    if embedding_result.dimension != EXPECTED_DIMENSION:
        raise RuntimeError(
            f"Expected {EXPECTED_DIMENSION}-dimensional embeddings, "
            f"got {embedding_result.dimension}."
        )

    if len(embedding_result.embeddings) != len(rows):
        raise RuntimeError(
            "Number of embeddings does not match number of chunks."
        )

    for row, embedding in zip(
        rows,
        embedding_result.embeddings,
        strict=True,
    ):
        if len(embedding) != EXPECTED_DIMENSION:
            raise RuntimeError(
                f"Chunk {row['id']} has invalid embedding dimension: "
                f"{len(embedding)}."
            )

        vector = "[" + ",".join(str(value) for value in embedding) + "]"

        (
            client.table("document_chunks")
            .update({"embedding": vector})
            .eq("id", str(row["id"]))
            .execute()
        )

        print(f"Embedded chunk: {row['id']}")

    print(f"Successfully embedded {len(rows)} chunks.")


if __name__ == "__main__":
    main()