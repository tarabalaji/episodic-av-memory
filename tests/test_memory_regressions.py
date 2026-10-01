from copy import deepcopy
import pytest
from src.memory.memory_builder import MemoryBuilder
from src.memory.memory_manager import MemoryManager
from src.memory.errors import MemoryCapacityError
from src.memory.strategies.core_safety import CoreSafetyStrategy
from src.memory.strategies.compression import CompressionStrategy
from src.memory.strategies.importance import ImportanceStrategy


def test_failed_insert_rolls_back_objects_and_capacity(event_factory):
    manager = MemoryManager(1, CoreSafetyStrategy())
    first = MemoryBuilder().build(event_factory(event_type="collision"))
    second = MemoryBuilder().build(event_factory(1, event_type="collision"))
    manager.add_memory(first)
    previous, incoming = deepcopy(first), deepcopy(second)
    with pytest.raises(MemoryCapacityError):
        manager.add_memory(second)
    assert manager.get_memories() == [previous]
    assert manager.get_memory(first.memory_id) is first
    assert second == incoming


def test_nonprogressing_strategy_fails_instead_of_hanging(event_factory):
    class Broken:
        def manage(self, memories):
            memories[0].description = "accidental mutation"
    manager = MemoryManager(1, Broken())
    first = MemoryBuilder().build(event_factory())
    manager.add_memory(first)
    before = deepcopy(first)
    with pytest.raises(RuntimeError, match="did not reduce"):
        manager.add_memory(MemoryBuilder().build(event_factory(1)))
    assert manager.get_memories() == [before]


@pytest.mark.parametrize("changes", [{"episode_id": "other"}, {"outcome": "failure"}, {"action": "brake"}])
def test_compression_never_merges_distinct_experiences(changes, event_factory):
    first = MemoryBuilder().build(event_factory())
    second = MemoryBuilder().build(event_factory(1, **changes))
    assert not CompressionStrategy()._similar(first, second)


def test_importance_recency_uses_global_order_across_episode_resets(event_factory):
    first = MemoryBuilder().build(event_factory(100, episode_id="old"))
    second = MemoryBuilder().build(event_factory(0, episode_id="new"))
    first.sequence_index, second.sequence_index = 0, 1
    manager = MemoryManager(1, ImportanceStrategy())
    manager.add_memory(first)
    manager.add_memory(second)
    assert manager.get_memories() == [second]


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -1])
def test_nonfinite_strategy_thresholds_rejected(threshold):
    with pytest.raises(ValueError):
        CompressionStrategy(threshold)
    with pytest.raises(ValueError):
        CoreSafetyStrategy(critical_ttc=threshold)
    with pytest.raises(ValueError):
        CoreSafetyStrategy(critical_distance=threshold)
