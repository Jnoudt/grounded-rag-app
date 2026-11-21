from src.eval.harness import EvaluationHarness


def test_golden_harness_metrics():
    report = EvaluationHarness(offline=True).run()
    assert report["case_count"] == 4
    assert report["metrics"]["retrieval_recall"] == 1.0
    assert report["metrics"]["citation_validity"] == 1.0
    assert report["metrics"]["abstention_accuracy"] == 1.0
    assert report["metrics"]["estimated_cost_usd"] == 0.0
