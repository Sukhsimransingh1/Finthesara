from app.ingestion.chunker import DocumentChunker
from app.ingestion.parser import ParsedPage


def test_short_page_creates_single_chunk() -> None:
    pages = [
        ParsedPage(
            page_number=1,
            text="Revenue increased by 14.2%.",
        )
    ]

    chunks = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    ).chunk(pages)

    assert len(chunks) == 1
    assert chunks[0].text == "Revenue increased by 14.2%."
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0


def test_long_page_creates_multiple_chunks() -> None:
    text = "Revenue increased significantly. " * 100

    pages = [
        ParsedPage(
            page_number=1,
            text=text,
        )
    ]

    chunks = DocumentChunker(
        chunk_size=200,
        chunk_overlap=40,
    ).chunk(pages)

    assert len(chunks) > 1

    for chunk in chunks:
        assert len(chunk.text) <= 200
        assert chunk.page_number == 1


def test_chunks_preserve_page_boundaries() -> None:
    pages = [
        ParsedPage(
            page_number=1,
            text="Page one content. " * 30,
        ),
        ParsedPage(
            page_number=2,
            text="Page two content. " * 30,
        ),
    ]

    chunks = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    ).chunk(pages)

    assert chunks

    page_numbers = {chunk.page_number for chunk in chunks}

    assert page_numbers == {1, 2}


def test_empty_pages_are_skipped() -> None:
    pages = [
        ParsedPage(page_number=1, text=""),
        ParsedPage(page_number=2, text="   "),
        ParsedPage(page_number=3, text="Actual content."),
    ]

    chunks = DocumentChunker().chunk(pages)

    assert len(chunks) == 1
    assert chunks[0].page_number == 3
    assert chunks[0].text == "Actual content."


def test_chunk_indices_are_global() -> None:
    pages = [
        ParsedPage(
            page_number=1,
            text="First page content. " * 50,
        ),
        ParsedPage(
            page_number=2,
            text="Second page content. " * 50,
        ),
    ]

    chunks = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    ).chunk(pages)

    indices = [chunk.chunk_index for chunk in chunks]

    assert indices == list(range(len(chunks)))


def test_invalid_chunk_size_is_rejected() -> None:
    try:
        DocumentChunker(chunk_size=0)
    except ValueError:
        return

    raise AssertionError("chunk_size=0 should raise ValueError")


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    try:
        DocumentChunker(
            chunk_size=100,
            chunk_overlap=100,
        )
    except ValueError:
        return

    raise AssertionError(
        "chunk_overlap >= chunk_size should raise ValueError"
    )