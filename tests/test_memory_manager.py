import pytest

from src.memory.memory_manager import MemoryManager
from src.memory.memory_schema import DrivingMemory
from src.memory.strategies.fifo import FIFOStrategy
from src.memory.strategies.importance import ImportanceStrategy


def create_memory(
    memory_id: str,
    timestamp: float,
    **overrides,
) -> DrivingMemory:
    values = {
        "memory_id": memory_id,
        "episode_id": "episode_001",
        "timestamp": timestamp,
        "event_type": "normal_driving",
        "description": "Test driving memory",
        "speed": 5.0,
        "distance_to_obstacle": 20.0,
        "time_to_collision": 5.0,
        "weather": "clear",
        "road_type": "urban",
        "action": "maintain",
        "outcome": "successful",
        "importance_score": 0.0,
        "protected": False,
        "access_count": 0,
    }

    values.update(overrides)
    return DrivingMemory(**values)


def create_fifo_manager(capacity: int = 3) -> MemoryManager:
    return MemoryManager(
        capacity=capacity,
        strategy=FIFOStrategy(),
    )


def create_importance_manager(
    capacity: int = 3,
) -> MemoryManager:
    return MemoryManager(
        capacity=capacity,
        strategy=ImportanceStrategy(),
    )


def get_memory_ids(manager: MemoryManager) -> list[str]:
    return [memory.memory_id for memory in manager.get_memories()]


def test_add_memory():
    manager = create_fifo_manager()
    memory = create_memory("memory_001", 1.0)

    manager.add_memory(memory)

    assert len(manager) == 1
    assert manager.get_memories() == [memory]


def test_fifo_removes_oldest_memory():
    manager = create_fifo_manager(capacity=3)

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))
    manager.add_memory(create_memory("memory_003", 3.0))
    manager.add_memory(create_memory("memory_004", 4.0))

    assert get_memory_ids(manager) == [
        "memory_002",
        "memory_003",
        "memory_004",
    ]


def test_fifo_keeps_newest_memories():
    manager = create_fifo_manager(capacity=2)

    manager.add_memory(create_memory("old", 1.0))
    manager.add_memory(create_memory("middle", 2.0))
    manager.add_memory(create_memory("new", 3.0))

    assert get_memory_ids(manager) == [
        "middle",
        "new",
    ]


def test_manager_never_exceeds_capacity():
    manager = create_fifo_manager(capacity=2)

    for index in range(10):
        manager.add_memory(
            create_memory(
                memory_id=f"memory_{index}",
                timestamp=float(index),
            )
        )

    assert len(manager) == 2


def test_get_existing_memory():
    manager = create_fifo_manager()
    memory = create_memory("memory_001", 1.0)

    manager.add_memory(memory)

    assert manager.get_memory("memory_001") is memory


def test_get_missing_memory():
    manager = create_fifo_manager()

    assert manager.get_memory("missing") is None


def test_remove_existing_memory():
    manager = create_fifo_manager()

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))

    removed = manager.remove_memory("memory_001")

    assert removed is True
    assert manager.get_memory("memory_001") is None
    assert len(manager) == 1


def test_remove_missing_memory():
    manager = create_fifo_manager()

    assert manager.remove_memory("missing") is False


def test_clear():
    manager = create_fifo_manager()

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))

    manager.clear()

    assert len(manager) == 0
    assert manager.get_memories() == []


def test_is_full():
    manager = create_fifo_manager(capacity=2)

    assert manager.is_full() is False

    manager.add_memory(create_memory("memory_001", 1.0))
    assert manager.is_full() is False

    manager.add_memory(create_memory("memory_002", 2.0))
    assert manager.is_full() is True


def test_get_memories_returns_copy():
    manager = create_fifo_manager()
    manager.add_memory(create_memory("memory_001", 1.0))

    returned_memories = manager.get_memories()
    returned_memories.clear()

    assert len(manager) == 1


def test_invalid_capacity():
    with pytest.raises(ValueError):
        MemoryManager(
            capacity=0,
            strategy=FIFOStrategy(),
        )


def test_negative_capacity():
    with pytest.raises(ValueError):
        MemoryManager(
            capacity=-1,
            strategy=FIFOStrategy(),
        )


def test_rejects_non_memory_object():
    manager = create_fifo_manager()

    with pytest.raises(TypeError):
        manager.add_memory("not a memory")


def test_fifo_rejects_empty_list():
    strategy = FIFOStrategy()

    with pytest.raises(ValueError):
        strategy.manage([])


def test_importance_removes_lowest_scoring_memory():
    manager = create_importance_manager(capacity=3)

    low_importance = create_memory(
        memory_id="low",
        timestamp=1.0,
        event_type="normal_driving",
        distance_to_obstacle=30.0,
        time_to_collision=10.0,
        action="maintain",
        outcome="successful",
        access_count=0,
    )

    high_importance = create_memory(
        memory_id="high",
        timestamp=2.0,
        event_type="collision",
        distance_to_obstacle=0.5,
        time_to_collision=0.3,
        action="emergency_brake",
        outcome="collision",
        access_count=5,
    )

    medium_importance = create_memory(
        memory_id="medium",
        timestamp=3.0,
        event_type="near_collision",
        distance_to_obstacle=4.0,
        time_to_collision=1.5,
        action="hard_brake",
        outcome="collision_avoided",
        access_count=2,
    )

    newest_importance = create_memory(
        memory_id="newest",
        timestamp=4.0,
        event_type="pedestrian_crossing",
        distance_to_obstacle=2.0,
        time_to_collision=0.8,
        action="emergency_brake",
        outcome="collision_avoided",
        access_count=1,
    )

    manager.add_memory(low_importance)
    manager.add_memory(high_importance)
    manager.add_memory(medium_importance)
    manager.add_memory(newest_importance)

    assert "low" not in get_memory_ids(manager)
    assert len(manager) == 3


def test_importance_updates_memory_scores():
    manager = create_importance_manager(capacity=2)

    manager.add_memory(
        create_memory(
            memory_id="normal",
            timestamp=1.0,
        )
    )

    manager.add_memory(
        create_memory(
            memory_id="collision",
            timestamp=2.0,
            event_type="collision",
            distance_to_obstacle=0.5,
            time_to_collision=0.4,
            action="emergency_brake",
            outcome="collision",
        )
    )

    manager.add_memory(
        create_memory(
            memory_id="near_collision",
            timestamp=3.0,
            event_type="near_collision",
            distance_to_obstacle=2.0,
            time_to_collision=0.8,
            action="hard_brake",
            outcome="collision_avoided",
        )
    )

    for memory in manager.get_memories():
        assert 0.0 <= memory.importance_score <= 1.0
        assert memory.importance_score > 0.0


def test_critical_memory_scores_higher_than_normal_memory():
    strategy = ImportanceStrategy()

    normal_memory = create_memory(
        memory_id="normal",
        timestamp=10.0,
    )

    critical_memory = create_memory(
        memory_id="critical",
        timestamp=10.0,
        event_type="collision",
        distance_to_obstacle=0.5,
        time_to_collision=0.3,
        action="emergency_brake",
        outcome="collision",
    )

    normal_score = strategy.calculate_score(
        memory=normal_memory,
        current_time=10.0,
    )

    critical_score = strategy.calculate_score(
        memory=critical_memory,
        current_time=10.0,
    )

    assert critical_score > normal_score


def test_recent_memory_scores_higher_than_old_memory():
    strategy = ImportanceStrategy()

    old_memory = create_memory(
        memory_id="old",
        timestamp=1.0,
    )

    recent_memory = create_memory(
        memory_id="recent",
        timestamp=10.0,
    )

    old_score = strategy.calculate_score(
        memory=old_memory,
        current_time=10.0,
    )

    recent_score = strategy.calculate_score(
        memory=recent_memory,
        current_time=10.0,
    )

    assert recent_score > old_score


def test_frequently_accessed_memory_scores_higher():
    strategy = ImportanceStrategy()

    unused_memory = create_memory(
        memory_id="unused",
        timestamp=10.0,
        access_count=0,
    )

    accessed_memory = create_memory(
        memory_id="accessed",
        timestamp=10.0,
        access_count=8,
    )

    unused_score = strategy.calculate_score(
        memory=unused_memory,
        current_time=10.0,
    )

    accessed_score = strategy.calculate_score(
        memory=accessed_memory,
        current_time=10.0,
    )

    assert accessed_score > unused_score


def test_importance_does_not_remove_protected_memory():
    manager = create_importance_manager(capacity=2)

    protected_memory = create_memory(
        memory_id="protected",
        timestamp=1.0,
        protected=True,
    )

    normal_memory = create_memory(
        memory_id="normal",
        timestamp=2.0,
    )

    critical_memory = create_memory(
        memory_id="critical",
        timestamp=3.0,
        event_type="collision",
        distance_to_obstacle=0.5,
        time_to_collision=0.3,
        action="emergency_brake",
        outcome="collision",
    )

    manager.add_memory(protected_memory)
    manager.add_memory(normal_memory)
    manager.add_memory(critical_memory)

    stored_ids = get_memory_ids(manager)

    assert "protected" in stored_ids
    assert "normal" not in stored_ids
    assert "critical" in stored_ids


def test_protected_memory_receives_maximum_score():
    strategy = ImportanceStrategy()

    memory = create_memory(
        memory_id="protected",
        timestamp=1.0,
        protected=True,
    )

    score = strategy.calculate_score(
        memory=memory,
        current_time=10.0,
    )

    assert score == 1.0


def test_importance_rejects_empty_list():
    strategy = ImportanceStrategy()

    with pytest.raises(ValueError):
        strategy.manage([])


def test_importance_rejects_all_protected_memories():
    strategy = ImportanceStrategy()

    memories = [
        create_memory(
            memory_id="protected_001",
            timestamp=1.0,
            protected=True,
        ),
        create_memory(
            memory_id="protected_002",
            timestamp=2.0,
            protected=True,
        ),
    ]

    with pytest.raises(RuntimeError):
        strategy.manage(memories)


def test_strategy_can_be_changed():
    manager = create_fifo_manager(capacity=2)

    manager.set_strategy(ImportanceStrategy())

    assert isinstance(
        manager.strategy,
        ImportanceStrategy,
    )
