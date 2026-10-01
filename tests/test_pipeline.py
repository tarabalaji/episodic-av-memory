from copy import deepcopy
from dataclasses import replace
import json
import pytest
from src.pipeline import run_pipeline
from src.memory.memory_database import MemoryDatabase
from src.simulation.data_logger import load_events
from src.utils.helpers import PROJECT_ROOT, STRATEGIES


@pytest.mark.parametrize("strategy", STRATEGIES + ("no_memory", "unlimited"))
def test_all_strategies_replay_without_future_or_self_retrieval(strategy, event_factory):
    events = [event_factory(i) for i in range(9)]
    before = deepcopy(events)
    report = run_pipeline(events, strategy=strategy, capacity=2)
    seen = set()
    for row in report["trace"]:
        assert {r["memory_id"] for r in row["retrieved"]} <= seen
        assert row["memory_id"] not in {r["memory_id"] for r in row["retrieved"]}
        seen.add(row["memory_id"])
        if strategy != "unlimited":
            assert len(row["retained_ids"]) <= 2
    assert events == before
    if strategy == "no_memory":
        assert report["metrics"]["retrieval_hit_rate"] == 0
        assert report["memories"] == []


def test_sample_pipeline_persists_exact_snapshot(tmp_path):
    events = load_events(PROJECT_ROOT / "data/raw/sample_events.json")
    report = run_pipeline(events, output_dir=tmp_path)
    assert report["metrics"]["events_processed"] == 10
    assert json.loads((tmp_path / "report.json").read_text()) == report
    with MemoryDatabase(tmp_path / "memories.sqlite3") as database:
        assert [m.to_dict() for m in database.load()] == report["memories"]


def test_protected_saturation_is_reported_without_overflow(event_factory):
    events = [event_factory(i, event_type="collision", outcome="collision") for i in range(6)]
    report = run_pipeline(events, strategy="core_safety", capacity=2)
    assert report["metrics"]["capacity_rejections"] == 4
    assert report["metrics"]["memories_retained"] == 2
    assert report["metrics"]["critical_event_retention"] == pytest.approx(2/6)


def test_compression_provenance_recall_and_coverage(event_factory):
    events = [event_factory(i) for i in range(8)]
    report = run_pipeline(events, strategy="compression", capacity=1)
    assert report["metrics"]["event_coverage"] == 1
    assert report["metrics"]["same_type_recall_at_k"] == 1
    assert report["memories"][0]["occurrence_count"] == 8
    assert report["memories"][0]["access_count"] == 7


def test_current_labels_and_retrospective_description_do_not_affect_plan_or_retrieval(event_factory):
    events = [event_factory(i) for i in range(3)]
    first = run_pipeline(events)["trace"][-1]
    events[-1] = replace(events[-1], action="emergency_steer", outcome="failure", description="SECRET_FUTURE_LABEL")
    second = run_pipeline(events)["trace"][-1]
    assert first["retrieved"] == second["retrieved"]
    assert first["plan"] == second["plan"]


def test_episode_reset_does_not_duplicate_ids(event_factory):
    events = [event_factory(0), event_factory(0, episode_id="next")]
    report = run_pipeline(events, capacity=2)
    assert len({m["memory_id"] for m in report["memories"]}) == 2


def test_empty_data_has_null_undefined_metrics():
    report = run_pipeline([])
    assert report["metrics"]["event_coverage"] is None
    assert report["metrics"]["critical_event_retention"] is None


def test_unordered_or_duplicate_events_rejected(event_factory):
    with pytest.raises(ValueError):
        run_pipeline([event_factory(2), event_factory(1)])
    with pytest.raises(ValueError):
        run_pipeline([event_factory(1), event_factory(1)])
