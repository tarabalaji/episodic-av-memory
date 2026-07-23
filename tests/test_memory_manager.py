import pytest

from src.memory.memory_manager import MemoryManager
from src.memory.memory_schema import DrivingMemory
from src.memory.strategies.fifo import FIFOStrategy


def create_memory(
    memory_id: str,
    timestamp: float,
) -> DrivingMemory:
    return DrivingMemory(
        memory_id=memory_id,
        episode_id="episode_001",
        timestamp=timestamp,
        event_type="test_event",
        description="Test driving memory",
        speed=5.0,
        distance_to_obstacle=10.0,
        time_to_collision=2.0,
        weather="clear",
        road_type="urban",
        action="maintain",
        outcome="successful",
        importance_score=0.0,
        protected=False,
        access_count=0,
    )


def create_manager(capacity: int = 3) -> MemoryManager:
    return MemoryManager(
        capacity=capacity,
        strategy=FIFOStrategy(),
    )


def test_add_memory():
    manager = create_manager()
    memory = create_memory("memory_001", 1.0)

    manager.add_memory(memory)

    assert len(manager) == 1
    assert manager.get_memories() == [memory]


def test_fifo_removes_oldest_memory():
    manager = create_manager(capacity=3)

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))
    manager.add_memory(create_memory("memory_003", 3.0))
    manager.add_memory(create_memory("memory_004", 4.0))

    stored_ids = [memory.memory_id for memory in manager.get_memories()]

    assert stored_ids == [
        "memory_002",
        "memory_003",
        "memory_004",
    ]


def test_manager_never_exceeds_capacity():
    manager = create_manager(capacity=2)

    for index in range(10):
        manager.add_memory(
            create_memory(
                memory_id=f"memory_{index}",
                timestamp=float(index),
            )
        )

    assert len(manager) == 2


def test_fifo_keeps_newest_memories():
    manager = create_manager(capacity=2)

    manager.add_memory(create_memory("old", 1.0))
    manager.add_memory(create_memory("middle", 2.0))
    manager.add_memory(create_memory("new", 3.0))

    stored_ids = [memory.memory_id for memory in manager.get_memories()]

    assert stored_ids == ["middle", "new"]


def test_get_existing_memory():
    manager = create_manager()
    memory = create_memory("memory_001", 1.0)

    manager.add_memory(memory)

    result = manager.get_memory("memory_001")

    assert result is memory


def test_get_missing_memory():
    manager = create_manager()

    result = manager.get_memory("missing")

    assert result is None


def test_remove_existing_memory():
    manager = create_manager()

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))

    removed = manager.remove_memory("memory_001")

    assert removed is True
    assert manager.get_memory("memory_001") is None
    assert len(manager) == 1


def test_remove_missing_memory():
    manager = create_manager()

    removed = manager.remove_memory("missing")

    assert removed is False


def test_clear():
    manager = create_manager()

    manager.add_memory(create_memory("memory_001", 1.0))
    manager.add_memory(create_memory("memory_002", 2.0))

    manager.clear()

    assert len(manager) == 0
    assert manager.get_memories() == []


def test_is_full():
    manager = create_manager(capacity=2)

    assert manager.is_full() is False

    manager.add_memory(create_memory("memory_001", 1.0))
    assert manager.is_full() is False

    manager.add_memory(create_memory("memory_002", 2.0))
    assert manager.is_full() is True


def test_get_memories_returns_copy():
    manager = create_manager()
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
    manager = create_manager()

    with pytest.raises(TypeError):
        manager.add_memory("not a memory")


def test_fifo_rejects_empty_list():
    strategy = FIFOStrategy()

    with pytest.raises(ValueError):
        strategy.manage([])
