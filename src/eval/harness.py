from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, cast

from src.rag.generator import GroundedAnswerGenerator
from src.rag.retriever import ChunkRetriever
from src.schemas.rag import AbstentionResult, GroundedRAGResponse


class EvaluationHarness:
    def __init__(
        self,
        *,
        golden_path: str | Path | None = None,
        offline: bool = True,
    ) -> None:
        default_path = Path(__file__).resolve().parents[2] / "data" / "golden_rag_cases.json"
        self.golden_path = Path(golden_path) if golden_path else default_path
        self.retriever = ChunkRetriever(offline=offline)
        self.generator = GroundedAnswerGenerator(offline=offline)

    def run(self) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        cases = json.loads(self.golden_path.read_text(encoding="utf-8"))
        results: list[dict[str, Any]] = []

        recall_hits = 0.0
        citation_valid = 0
        abstention_correct = 0
        latencies_ms: list[float] = []
        estimated_input_tokens = 0
        estimated_output_tokens = 0

        for index, case in enumerate(cases):
            started = time.perf_counter()
            query = str(case["query"])
            chunks = self.retriever.retrieve(query)
            response = self.generator.generate(
                query,
                chunks,
                request_id=f"{run_id}-case-{index}",
                trace_id=f"{run_id}-case-{index}",
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(elapsed_ms)

            is_abstention = isinstance(response, AbstentionResult)
            expected_abstention = bool(case["expected_abstention"])
            if is_abstention == expected_abstention:
                abstention_correct += 1

            retrieved_ids = {chunk.chunk_id for chunk in chunks}
            expected_ids = set(case["expected_chunk_ids"])
            if not expected_ids:
                recall = 1.0
            else:
                recall = len(retrieved_ids & expected_ids) / len(expected_ids)
            recall_hits += recall

            if is_abstention:
                case_citations_valid = True
            else:
                grounded_response = cast(GroundedRAGResponse, response)
                cited_ids = {
                    chunk_id
                    for claim in grounded_response.claims
                    for chunk_id in claim.chunk_ids
                }
                case_citations_valid = bool(cited_ids) and cited_ids.issubset(retrieved_ids)
            if case_citations_valid:
                citation_valid += 1

            estimated_input_tokens += max(1, len(query) // 4)
            output_text = response.answer
            estimated_output_tokens += max(1, len(output_text) // 4)

            results.append(
                {
                    "id": case["id"],
                    "query": query,
                    "abstained": is_abstention,
                    "retrieval_recall": recall,
                    "citation_valid": case_citations_valid,
                    "abstention_correct": is_abstention == expected_abstention,
                    "latency_ms": round(elapsed_ms, 3),
                    "result": response.model_dump(mode="json"),
                }
            )

        case_count = max(1, len(cases))
        avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
        metrics = {
            "retrieval_recall": round(recall_hits / case_count, 4),
            "citation_validity": round(citation_valid / case_count, 4),
            "abstention_accuracy": round(abstention_correct / case_count, 4),
            "average_latency_ms": round(avg_latency, 3),
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_total_tokens": estimated_input_tokens + estimated_output_tokens,
            "estimated_cost_usd": 0.0,
        }
        return {
            "run_id": run_id,
            "mode": "offline" if self.retriever.offline else "live",
            "case_count": len(cases),
            "metrics": metrics,
            "results": results,
        }
