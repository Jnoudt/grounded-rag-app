from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkOffset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @field_validator("end")
    @classmethod
    def validate_range(cls, end: int, info) -> int:
        start = info.data.get("start")
        if start is not None and end <= start:
            raise ValueError("end must be greater than start")
        return end


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*_p\d+_c\d+$")
    doc_slug: str = Field(min_length=1)
    page_number: int = Field(default=1, ge=1)
    section: str | None = None
    offsets: ChunkOffset
    text: str = Field(min_length=1)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)


class CitedSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    quote: str = Field(min_length=1)
    offsets: ChunkOffset


class CitedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    chunk_ids: list[str] = Field(min_length=1)
    spans: list[CitedSpan] = Field(default_factory=list)
    support_score: float | None = Field(default=None, ge=0.0, le=1.0)


class AnswerMode(str, Enum):
    GROUNDED = "grounded"
    OFFLINE_MOCK = "offline_mock"
    ABSTAINED = "abstained"


class RetrievalProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    retrieval_query: str = Field(min_length=1)
    relevance_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    support_threshold: float = Field(default=0.50, ge=0.0, le=1.0)


class GroundedRAGResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    trace_id: str | None = None
    mode: AnswerMode
    query: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    claims: list[CitedClaim] = Field(default_factory=list)
    retrieved_chunks: list[DocumentChunk] = Field(default_factory=list)
    provenance: RetrievalProvenance


class AbstentionReason(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNKNOWN_CHUNK_CITATION = "unknown_chunk_citation"
    WEAK_RELEVANCE = "weak_relevance"
    WEAK_SUPPORT = "weak_support"
    EMPTY_QUERY = "empty_query"
    NO_CITED_CLAIMS = "no_cited_claims"


class AbstentionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    abstained: Literal[True] = True
    reason: AbstentionReason
    answer: str = "I cannot answer this request because the available evidence is insufficient."
    invalid_chunk_ids: list[str] = Field(default_factory=list)
    weak_claim_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class MetricStatus(str, Enum):
    PASS = "pass"  # nosec B105 - enum status label, not a credential
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class EvaluationMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: float
    threshold: float
    status: MetricStatus
    passed: bool
    details: dict[str, object] = Field(default_factory=dict)


class EvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    overall_passed: bool
