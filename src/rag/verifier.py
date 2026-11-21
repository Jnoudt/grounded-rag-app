from __future__ import annotations

import re
from collections import Counter

from src.schemas.rag import (
    AbstentionReason,
    AbstentionResult,
    CitedClaim,
    DocumentChunk,
    GroundedRAGResponse,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer)\s+[^\s]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+"),
)


def sanitize_untrusted_context(text: str) -> str:
    sanitized = text.replace("\r", " ").replace("\n", " ").replace("\x00", "")
    sanitized = re.sub(r"\b(SYSTEM|DEVELOPER)\s*:", r"<instruction-tag>\1:</instruction-tag>", sanitized, flags=re.I)
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(r"\1=<redacted>", sanitized)
    return (
        "UNTRUSTED_DOCUMENT_CONTEXT_BEGIN\n"
        f"{sanitized}\n"
        "UNTRUSTED_DOCUMENT_CONTEXT_END"
    )


def tokenize(text: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(text.lower()))


def lexical_support(claim_text: str, evidence_text: str) -> float:
    claim_tokens = tokenize(claim_text)
    evidence_tokens = tokenize(evidence_text)
    if not claim_tokens:
        return 0.0

    overlap = sum(
        min(count, evidence_tokens[token])
        for token, count in claim_tokens.items()
    )
    return overlap / sum(claim_tokens.values())


class CitationGroundingVerifier:
    def __init__(
        self,
        relevance_threshold: float = 0.35,
        support_threshold: float = 0.50,
    ) -> None:
        if not 0.0 <= relevance_threshold <= 1.0:
            raise ValueError("relevance_threshold must be between 0 and 1")
        if not 0.0 <= support_threshold <= 1.0:
            raise ValueError("support_threshold must be between 0 and 1")
        self.relevance_threshold = relevance_threshold
        self.support_threshold = support_threshold

    def verify(
        self,
        response: GroundedRAGResponse,
    ) -> AbstentionResult | GroundedRAGResponse:
        if not response.query.strip():
            return self._abstain(
                AbstentionReason.EMPTY_QUERY,
                trace_id=response.trace_id,
            )

        chunk_map = {
            chunk.chunk_id: chunk
            for chunk in response.retrieved_chunks
        }

        invalid_ids: list[str] = []
        weak_claim_ids: list[str] = []

        if not response.claims:
            return self._abstain(
                AbstentionReason.NO_CITED_CLAIMS,
                trace_id=response.trace_id,
            )

        for claim in response.claims:
            for chunk_id in claim.chunk_ids:
                if chunk_id not in chunk_map:
                    invalid_ids.append(chunk_id)
                    continue

                chunk = chunk_map[chunk_id]
                relevance = (
                    chunk.relevance_score
                    if chunk.relevance_score is not None
                    else lexical_support(response.query, chunk.text)
                )
                evidence_support = lexical_support(claim.text, chunk.text)
                if relevance < self.relevance_threshold:
                    weak_claim_ids.append(claim.claim_id)
                if evidence_support < self.support_threshold:
                    weak_claim_ids.append(claim.claim_id)

        weak_claim_ids = sorted(set(weak_claim_ids))
        invalid_ids = sorted(set(invalid_ids))

        if invalid_ids:
            return self._abstain(
                AbstentionReason.UNKNOWN_CHUNK_CITATION,
                invalid_chunk_ids=invalid_ids,
                weak_claim_ids=weak_claim_ids,
                trace_id=response.trace_id,
            )
        if weak_claim_ids:
            return self._abstain(
                AbstentionReason.WEAK_SUPPORT,
                weak_claim_ids=weak_claim_ids,
                trace_id=response.trace_id,
            )

        return response

    def verify_claim(
        self,
        claim: CitedClaim,
        retrieved_chunks: list[DocumentChunk],
    ) -> bool:
        chunk_map = {chunk.chunk_id: chunk for chunk in retrieved_chunks}
        if not claim.chunk_ids:
            return False

        for chunk_id in claim.chunk_ids:
            chunk = chunk_map.get(chunk_id)
            if chunk is None:
                return False
            relevance = (
                chunk.relevance_score
                if chunk.relevance_score is not None
                else lexical_support(claim.text, chunk.text)
            )
            if relevance < self.relevance_threshold:
                return False
            if lexical_support(claim.text, chunk.text) < self.support_threshold:
                return False
        return True

    def _abstain(
        self,
        reason: AbstentionReason,
        *,
        invalid_chunk_ids: list[str] | None = None,
        weak_claim_ids: list[str] | None = None,
        trace_id: str | None = None,
    ) -> AbstentionResult:
        return AbstentionResult(
            reason=reason,
            invalid_chunk_ids=invalid_chunk_ids or [],
            weak_claim_ids=weak_claim_ids or [],
            trace_id=trace_id,
        )
