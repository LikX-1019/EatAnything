from app.core.metrics import Metrics


def test_metrics_use_controlled_paths_without_identifiers() -> None:
    metrics = Metrics()
    metrics.observe_request("GET", "/api/v1/stores/123", 200, 4.2)
    metrics.observe_request("POST", "/api/v1/stores/random", 200, 8.4)
    metrics.observe_exception()
    output = metrics.render()
    assert 'path="/api/v1/stores/:id"' in output
    assert 'path="/api/v1/stores/random"' in output
    assert "123" not in output
    assert "eatanything_unhandled_exceptions_total 1" in output
