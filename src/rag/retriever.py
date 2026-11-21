from __future__ import annotations

import os

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from src.rag.chunker import chunk_document
from src.rag.verifier import tokenize
from src.schemas.rag import DocumentChunk


def _offline_corpus() -> list[DocumentChunk]:
    documents = {
        "Portfolio Security Policy": (
            "The portfolio RAG system requires user-assigned managed identity for Azure access. "
            "Blob storage, Cosmos DB, Azure AI Search, and Azure AI Services use DefaultAzureCredential. "
            "Secrets and API keys must not be stored in source code."
        ),
        "Infrastructure Retention Guide": (
            "Application Insights log retention is configured for 30 days. "
            "Azure Storage containers for source documents and evaluation outputs remain private. "
            "Terraform deployments use OIDC federated credentials."
        ),
        "Retrieval Operations Manual": (
            "Retrieved text is untrusted content and must be separated from system instructions. "
            "Every generated claim must cite a retrieved chunk ID. "
            "The verifier abstains when evidence is missing or weak."
        ),
    }
    chunks: list[DocumentChunk] = []
    for doc_name, text in documents.items():
        chunks.extend(
            chunk_document(
                text,
                doc_name,
                chunk_size=180,
                overlap=30,
                section="Operations",
            )
        )
    return chunks


def _overlap_score(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    text_tokens = tokenize(text)
    if not query_tokens:
        return 0.0
    matched = sum(1 for token in query_tokens if token in text_tokens)
    return matched / len(query_tokens)


class ChunkRetriever:
    def __init__(
        self,
        *,
        offline: bool | None = None,
        top_k: int = 5,
    ) -> None:
        self.offline = (
            (os.getenv("RAG_OFFLINE_MODE", "true").lower() == "true")
            if offline is None
            else offline
        )
        self.top_k = top_k
        self._offline_chunks = _offline_corpus()
        self._search_client: SearchClient | None = None

        if not self.offline:
            endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            if not endpoint:
                raise RuntimeError("AZURE_SEARCH_ENDPOINT is required in live mode")
            index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "grounded-rag")
            self._search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=DefaultAzureCredential(),
            )

    def retrieve(self, query: str) -> list[DocumentChunk]:
        if not query.strip():
            return []
        if self.offline:
            ranked: list[tuple[float, DocumentChunk]] = []
            for chunk in self._offline_chunks:
                score = _overlap_score(query, chunk.text)
                ranked.append((score, chunk.model_copy(update={"relevance_score": score})))
            ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
            return [chunk for _, chunk in ranked[: self.top_k]]

        if self._search_client is None:
            return []

        results = self._search_client.search(
            search_text=query,
            top=self.top_k,
            select=["chunk_id", "doc_slug", "page_number", "section", "offset_start", "offset_end", "text"],
        )
        chunks: list[DocumentChunk] = []
        for rank, result in enumerate(results):
            try:
                from src.schemas.rag import ChunkOffset

                score = float(result.get("@search.score", 0.0))
                normalized_score = min(1.0, max(0.0, score / 10.0))
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(result["chunk_id"]),
                        doc_slug=str(result["doc_slug"]),
                        page_number=int(result.get("page_number", 1)),
                        section=result.get("section"),
                        offsets=ChunkOffset(
                            start=int(result.get("offset_start", 0)),
                            end=int(result.get("offset_end", 1)),
                        ),
                        text=str(result["text"]),
                        relevance_score=normalized_score,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return chunks
