from src.rag.generator import GroundedAnswerGenerator
from src.rag.retriever import ChunkRetriever
from src.schemas.rag import AbstentionResult


def test_offline_retriever_returns_provenance_chunks():
    chunks = ChunkRetriever(offline=True).retrieve("How does Azure access use identity?")
    assert chunks
    assert all(chunk.chunk_id and chunk.page_number >= 1 for chunk in chunks)
    assert all(chunk.offsets.start <= chunk.offsets.end for chunk in chunks)


def test_offline_generator_returns_verified_claim():
    retriever = ChunkRetriever(offline=True)
    chunks = retriever.retrieve("What is the Application Insights log retention?")
    result = GroundedAnswerGenerator(
        offline=True,
        relevance_threshold=0.35,
        support_threshold=0.50,
    ).generate(
        "What is the Application Insights log retention?",
        chunks,
        request_id="test-request",
        trace_id="test-trace",
    )
    assert getattr(result, "abstained", False) is False
    assert result.claims
    assert result.claims[0].chunk_ids


def test_offline_generator_abstains_for_empty_evidence():
    result = GroundedAnswerGenerator(offline=True).generate(
        "Unrelated question",
        [],
        request_id="test-request",
    )
    assert isinstance(result, AbstentionResult)
    assert result.reason.value == "insufficient_evidence"
