import json

import function_app


class FakeRequest:
    def __init__(self, body=None, headers=None):
        self.headers = headers or {}
        self._body = body

    def get_json(self):
        if isinstance(self._body, (dict, list)):
            return self._body
        raise ValueError("invalid JSON")

    def get_body(self):
        return b"" if self._body is None else json.dumps(self._body).encode()


def response_json(response):
    return json.loads(response.get_body())


def test_health_endpoint():
    response = function_app.health(FakeRequest(headers={"x-correlation-id": "trace-health"}))
    assert response.status_code == 200
    payload = response_json(response)
    assert payload["status"] == "healthy"
    assert payload["trace_id"] == "trace-health"


def test_query_endpoint_offline(monkeypatch):
    monkeypatch.setenv("RAG_OFFLINE_MODE", "true")
    response = function_app.query(
        FakeRequest(
            body={"query": "How does Azure access use identity?", "top_k": 3},
            headers={"x-correlation-id": "trace-query"},
        )
    )
    assert response.status_code == 200
    payload = response_json(response)
    assert "answer" in payload
    assert payload["trace_id"] == "trace-query"


def test_invalid_query_request():
    response = function_app.query(FakeRequest(body={"top_k": 0}))
    assert response.status_code == 400
    payload = response_json(response)
    assert payload["error"]["code"] == "invalid_request"


def test_eval_run_and_latest(monkeypatch):
    monkeypatch.setenv("RAG_OFFLINE_MODE", "true")
    run = function_app.eval_run(
        FakeRequest(body={"offline": True}, headers={"x-correlation-id": "trace-eval"})
    )
    assert run.status_code == 200
    run_payload = response_json(run)
    assert run_payload["metrics"]["retrieval_recall"] == 1.0

    latest = function_app.eval_latest(
        FakeRequest(headers={"x-correlation-id": "trace-latest"})
    )
    assert latest.status_code == 200
    assert response_json(latest)["run_id"] == run_payload["run_id"]
