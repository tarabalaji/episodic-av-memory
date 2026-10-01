import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.planner.llm_planner import LLMPlanner, observation
from src.memory.memory_builder import MemoryBuilder
from src.retrieval.retriever import RetrievalResult


def test_openai_adapter_validates_output_and_excludes_current_labels(event_factory):
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(
        output_text='{"action":"slow_down","reason":"Rain limits visibility."}'))))
    event = event_factory(description="SECRET_OUTCOME", action="secret_action", outcome="secret_outcome")
    plan = LLMPlanner("openai", "test-model", client).plan(event, [])
    assert plan.action == "slow_down" and plan.source == "openai"
    payload = json.loads(client.responses.create.call_args.kwargs["input"])
    assert payload["observation"] == observation(event)
    assert "description" not in payload["observation"]
    assert "outcome" not in payload["observation"] and "action" not in payload["observation"]


@pytest.mark.parametrize("response", ["not JSON", "[]", '{"action":"accelerate","reason":"go"}',
                                     '{"action":"stop","reason":""}', 'null'])
def test_invalid_llm_output_is_not_silently_a_valid_plan(response, event_factory):
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(output_text=response))))
    with pytest.raises(ValueError, match="invalid plan"):
        LLMPlanner("openai", "test-model", client).plan(event_factory(), [])


def test_rules_use_memory_and_handle_unknown_measurements(event_factory):
    event = event_factory(time_to_collision=None, distance_to_obstacle=None)
    planner = LLMPlanner()
    assert planner.plan(event, []).action == "maintain"
    past = MemoryBuilder().build(event_factory(1, outcome="failure"))
    assert planner.plan(event, [RetrievalResult(past, .9)]).action == "slow_down"
