from copy import deepcopy
import json
import math
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.evaluation.annotations import validate_annotations
from src.evaluation.protocol import validate_protocol
from src.evaluation.ranking import ranked_metrics
from src.evaluation.experiments import evaluate, grouped_interval, interval
from src.evaluation.output import experiment_directory
from src.pipeline import run_pipeline
from src.memory.memory_schema import DrivingMemory
from src.retrieval.retriever import RetrievalResult


def annotations(events):
    return {"schema_version": 1, "label_source": "synthetic_demo", "queries": [
        {"episode_id": events[-1].episode_id, "event_id": events[-1].event_id,
         "query": "observed urban road", "relevance": {e.event_id: 1 for e in events[:-1]}}]}


def test_hand_calculated_ranking_scores(event_factory):
    memories = [DrivingMemory.from_event(event_factory(i)) for i in range(3)]
    grades = dict(zip([m.memory_id for m in memories], [3, 0, 1]))
    found = [RetrievalResult(memories[1], .9), RetrievalResult(memories[0], .8)]
    scores = ranked_metrics(found, grades, 2)
    assert scores["annotated_precision_at_k"] == .5
    assert scores["annotated_source_recall_at_k"] == .5
    assert scores["annotated_mrr_at_k"] == .5
    assert scores["annotated_ndcg_at_k"] == pytest.approx((7 / math.log2(3)) / (7 + 1 / math.log2(3)))


def test_compression_grades_sources_without_double_counting(event_factory):
    memories = [DrivingMemory.from_event(event_factory(i)) for i in range(3)]
    grades = {m.memory_id: 1 for m in memories}
    memories[0].source_memory_ids.append(memories[1].memory_id)
    scores = ranked_metrics([RetrievalResult(memories[0], 1)], grades, 2)
    assert scores["annotated_source_recall_at_k"] == pytest.approx(2/3)
    assert scores["annotated_precision_at_k"] == .5
    assert 0 <= scores["annotated_ndcg_at_k"] <= 1
    with pytest.raises(ValueError, match="disjoint"):
        ranked_metrics([RetrievalResult(memories[0], 1), RetrievalResult(memories[1], .5)], grades, 2)


def test_no_relevant_results_preserves_undefined_metrics():
    scores = ranked_metrics([], {"m": 0}, 3)
    assert scores["annotated_precision_at_k"] == 0
    assert scores["annotated_source_recall_at_k"] is None
    assert scores["annotated_mrr_at_k"] is None
    assert scores["annotated_ndcg_at_k"] is None


def test_future_self_and_unjudged_references_rejected(event_factory):
    events = [event_factory(i) for i in range(3)]
    for grades in ({"e0": 1}, {"e0": 1, "e1": 1, "e2": 1}, {"e0": 1, "e1": 1, "future": 0}):
        payload = annotations(events)
        payload["queries"][0]["relevance"] = grades
        with pytest.raises(ValueError, match="exactly all earlier"):
            validate_annotations(events, payload)


@pytest.mark.parametrize("grade", [-1, 4, 1.5, True, "1"])
def test_malformed_grades_rejected(grade, event_factory):
    events = [event_factory(i) for i in range(2)]
    payload = annotations(events)
    payload["queries"][0]["relevance"]["e0"] = grade
    with pytest.raises(ValueError, match="grades"):
        validate_annotations(events, payload)


def test_relevance_labels_never_affect_retrieval_or_plans(event_factory):
    events = [event_factory(i) for i in range(4)]
    payload = annotations(events)
    first = run_pipeline(events, annotations=payload)
    payload["queries"][0]["relevance"] = {f"e{i}": 0 for i in range(3)}
    second = run_pipeline(events, annotations=payload)
    for a, b in zip(first["trace"], second["trace"]):
        assert a["retrieved"] == b["retrieved"]
        assert a["plan"] == b["plan"]
    assert first["memories"] == second["memories"]
    assert first["metrics"]["annotated_source_recall_at_k"] == 1
    assert second["metrics"]["annotated_source_recall_at_k"] is None


def test_invalid_sequence_is_rejected_before_any_planning(event_factory):
    planner = Mock()
    with pytest.raises(ValueError):
        run_pipeline([event_factory(0), event_factory(2), event_factory(1)], planner=planner)
    planner.plan.assert_not_called()


def test_scenario_group_cannot_cross_splits(event_factory):
    events = [event_factory(0, episode_id="a"), event_factory(0, episode_id="b")]
    payload = {"schema_version": 1, "episodes": {
        "a": {"group_id": "same_route", "split": "train"},
        "b": {"group_id": "same_route", "split": "test"}}}
    with pytest.raises(ValueError, match="crosses"):
        validate_protocol(events, payload, "test")
    payload["episodes"]["a"]["group_id"] = "another_route"
    selected, groups = validate_protocol(events, payload, "test")
    assert selected == {"b"} and groups == {"b": "same_route"}


def test_group_weighting_does_not_count_repeated_episodes_as_independent():
    rows = [{"episode_id": "a", "score": 0}, {"episode_id": "b", "score": 0},
            {"episode_id": "c", "score": 1}]
    result = grouped_interval(rows, "score", {"a": "route1", "b": "route1", "c": "route2"}, 42, 100)
    assert result["mean"] == .5
    assert result["n"] == 2 and result["n_episodes"] == 3


def test_output_refuses_overwrite_and_preserves_failed_run(tmp_path):
    destination = tmp_path / "run"
    with pytest.raises(RuntimeError):
        with experiment_directory(destination):
            raise RuntimeError("intentional failure")
    status = (destination / "run_status.json").read_text()
    assert json.loads(status)["status"] == "failed"
    with pytest.raises(FileExistsError):
        with experiment_directory(destination):
            pytest.fail("Must not enter an existing run")
    assert (destination / "run_status.json").read_text() == status
    assert not (destination / ".experiment.lock").exists()


def test_annotation_evaluation_is_reproducible_and_uses_only_test_split(tmp_path, event_factory):
    events = [event_factory(i, episode_id=episode) for episode in ("train_ep", "test_ep") for i in range(4)]
    payload = annotations(events[4:])
    protocol = {"schema_version": 1, "episodes": {
        "train_ep": {"group_id": "training_route", "split": "train"},
        "test_ep": {"group_id": "test_route", "split": "test"}}}
    results = [evaluate(events, tmp_path / f"run{i}", [2], annotations=payload,
                        protocol=protocol, split="test", bootstrap_samples=100) for i in range(2)]
    assert all(row["episode_id"] == "test_ep" for row in results[0]["episodes"])
    assert all(row["ci_low"] is None for row in results[0]["summary"])
    for result in results:
        assert len(result["manifest"]["annotations_sha256"]) == 64
        assert result["manifest"]["settings"]["label_source"] == "synthetic_demo"
    stable = lambda result: [row for row in result["summary"] if row["metric"] != "mean_retrieval_ms"]
    assert stable(results[0]) == stable(results[1])
    assert json.loads((tmp_path / "run0/run_status.json").read_text())["status"] == "complete"


def test_bad_protocol_leaves_no_partial_output(tmp_path, event_factory):
    output = tmp_path / "bad"
    with pytest.raises(ValueError):
        evaluate([event_factory()], output, protocol={"schema_version": 1, "episodes": {}}, split="test")
    assert not output.exists()


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_statistics_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        interval([value], samples=100)


@pytest.mark.parametrize("extra", ["capacity: 10", "typo_capacity: 5", "similarity_window: .nan", "planner: openai"])
def test_invalid_experiment_config_rejected(tmp_path, extra):
    from src.utils.helpers import load_config
    config = tmp_path / "config.yaml"
    config.write_text("events_path: events.json\noutput_dir: out\ncapacity: 5\ntop_k: 3\nstrategy: fifo\nplanner: rule_based\n" + extra + "\n")
    with pytest.raises(ValueError):
        load_config(config)


@pytest.mark.parametrize("payload", ['{"episode": "train", "episode": "test"}', '{"grade": NaN}'])
def test_ambiguous_json_is_rejected(payload):
    from src.utils.helpers import loads_json
    with pytest.raises(ValueError):
        loads_json(payload)
