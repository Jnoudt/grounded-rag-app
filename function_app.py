from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from typing import Any

import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.eval.harness import EvaluationHarness
from src.rag.generator import GroundedAnswerGenerator
from src.rag.retriever import ChunkRetriever


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
_latest_eval: dict[str, Any] | None = None
_latest_eval_lock = threading.Lock()


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    trace_id: str | None = Field(default=None, max_length=128)


def _trace_id(req: func.HttpRequest) -> str:
    supplied = req.headers.get("x-correlation-id") or req.headers.get("traceparent")
    return supplied[:128] if supplied else str(uuid.uuid4())


def _json_response(payload: dict[str, Any], status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
        headers={"Cache-Control": "no-store"},
    )


def _error_response(trace_id: str, status: int, code: str) -> func.HttpResponse:
    return _json_response(
        {
            "error": {
                "code": code,
                "message": "The request could not be processed.",
                "trace_id": trace_id,
            }
        },
        status=status,
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def health(req: func.HttpRequest) -> func.HttpResponse:
    trace_id = _trace_id(req)
    offline = os.getenv("RAG_OFFLINE_MODE", "true").lower() == "true"
    payload = {
        "status": "healthy",
        "mode": "offline" if offline else "live",
        "trace_id": trace_id,
    }
    logging.info(json.dumps({"event": "health", "trace_id": trace_id, "mode": payload["mode"]}))
    return _json_response(payload)


@app.route(route="query", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def query(req: func.HttpRequest) -> func.HttpResponse:
    trace_id = _trace_id(req)
    try:
        raw = req.get_json()
        request = QueryRequest.model_validate(raw)
    except (ValueError, ValidationError):
        return _error_response(trace_id, 400, "invalid_request")

    effective_trace_id = request.trace_id or trace_id
    try:
        retriever = ChunkRetriever(top_k=request.top_k)
        chunks = retriever.retrieve(request.query)
        generator = GroundedAnswerGenerator()
        result = generator.generate(
            request.query,
            chunks,
            request_id=str(uuid.uuid4()),
            trace_id=effective_trace_id,
        )
        payload = result.model_dump(mode="json")
        logging.info(
            json.dumps(
                {
                    "event": "rag_query",
                    "trace_id": effective_trace_id,
                    "abstained": getattr(result, "abstained", False),
                    "retrieved_count": len(chunks),
                }
            )
        )
        return _json_response(payload)
    except Exception:
        logging.exception(
            json.dumps(
                {
                    "event": "rag_query_error",
                    "trace_id": effective_trace_id,
                    "error": "request_processing_failed",
                }
            )
        )
        return _error_response(effective_trace_id, 503, "service_unavailable")


@app.route(route="eval/run", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def eval_run(req: func.HttpRequest) -> func.HttpResponse:
    global _latest_eval
    trace_id = _trace_id(req)
    try:
        offline = os.getenv("RAG_OFFLINE_MODE", "true").lower() == "true"
        if req.get_body():
            raw = req.get_json()
            if isinstance(raw, dict) and "offline" in raw:
                offline = bool(raw["offline"])
        report = EvaluationHarness(offline=offline).run()
        with _latest_eval_lock:
            _latest_eval = report
            _latest_eval["trace_id"] = trace_id
        logging.info(
            json.dumps(
                {
                    "event": "evaluation_run",
                    "trace_id": trace_id,
                    "run_id": report["run_id"],
                    "mode": report["mode"],
                }
            )
        )
        return _json_response(report)
    except Exception:
        logging.exception(
            json.dumps(
                {
                    "event": "evaluation_error",
                    "trace_id": trace_id,
                    "error": "evaluation_failed",
                }
            )
        )
        return _error_response(trace_id, 500, "evaluation_failed")


@app.route(route="eval/latest", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def eval_latest(req: func.HttpRequest) -> func.HttpResponse:
    trace_id = _trace_id(req)
    with _latest_eval_lock:
        report = None if _latest_eval is None else dict(_latest_eval)
    if report is None:
        return _error_response(trace_id, 404, "evaluation_not_found")
    return _json_response(report)
