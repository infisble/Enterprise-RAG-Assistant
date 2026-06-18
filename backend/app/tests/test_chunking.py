from app.services.chunking import TextChunker


def test_chunker_preserves_text_with_overlap() -> None:
    text = "Sentence one. Sentence two is longer. Sentence three closes the sample."
    chunks = TextChunker(chunk_size=32, overlap=8).split(text)

    assert len(chunks) > 1
    assert chunks[0].startswith("Sentence one")
    assert all(chunk.strip() for chunk in chunks)


def test_chunker_ignores_empty_text() -> None:
    assert TextChunker(chunk_size=100, overlap=10).split(" \n\t ") == []
