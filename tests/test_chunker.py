import pytest

from src.rag.chunker import DeterministicChunker, chunk_document


def test_chunk_ids_and_offsets_are_deterministic():
    text = "Alpha beta gamma. " * 20
    first = chunk_document(text, "Policy Guide", chunk_size=80, overlap=10)
    second = chunk_document(text, "Policy Guide", chunk_size=80, overlap=10)

    assert first == second
    assert first
    assert first[0].chunk_id == "policy-guide_p1_c1"
    assert first[0].offsets.start == 0
    assert all(chunk.page_number == 1 for chunk in first)


def test_multiple_pages_reset_chunk_indices():
    chunks = chunk_document("page one", "Guide", pages=["first page", "second page"])
    assert [chunk.chunk_id for chunk in chunks] == [
        "guide_p1_c1",
        "guide_p2_c1",
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, 10), (10, -1)],
)
def test_invalid_chunk_controls(chunk_size, overlap):
    with pytest.raises(ValueError):
        DeterministicChunker(chunk_size=chunk_size, overlap=overlap)
