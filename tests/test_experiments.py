import pytest
from src.evaluation.experiments import evaluate, interval
from scripts.generate_benchmark import generate_benchmark


def test_bootstrap_is_reproducible_and_handles_undefined_metrics():
    assert interval([.1, .4, .6], 123, 100) == interval([.1, .4, .6], 123, 100)
    assert interval([None])["mean"] is None
    assert interval([.5])["ci_low"] is None


def test_experiment_runs_all_baselines_with_paired_zero_fifo_differences(tmp_path):
    events = generate_benchmark(3, 12, 42)
    result = evaluate(events, tmp_path, [2], bootstrap_samples=100)
    assert len(result["episodes"]) == 18
    fifo = [r for r in result["paired_differences_vs_fifo"] if r["strategy"] == "fifo"]
    assert all(r["mean"] in (None, 0) for r in fifo)
    for path in ["comparison.json", "comparison.html", "episodes.csv", "summary.csv", "manifest.json"]:
        assert (tmp_path / path).is_file()
    for row in result["summary"]:
        if row["metric"] == "critical_event_retention" and row["mean"] is not None:
            assert 0 <= row["mean"] <= 1
    assert len(result["manifest"]["data_sha256"]) == 64


def test_synthetic_generation_reproducible():
    assert generate_benchmark(2, 10, 5) == generate_benchmark(2, 10, 5)
    assert generate_benchmark(2, 10, 5) != generate_benchmark(2, 10, 6)


def test_empty_experiment_rejected(tmp_path):
    with pytest.raises(ValueError):
        evaluate([], tmp_path)
