from src.memory.memory_manager import MemoryManager
from src.memory.memory_schema import DrivingMemory


def create_memory(memory_id: str, timestamp: float) -> DrivingMemory:
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
    )


def test_fifo_removes_oldest_memory():
    manager = MemoryManager(capacity=3)

    manager.add_memory(create_memory("mem_001", 1.0))
    manager.add_memory(create_memory("mem_002", 2.0))
    manager.add_memory(create_memory("mem_003", 3.0))
    manager.add_memory(create_memory("mem_004", 4.0))

    stored_ids = [memory.memory_id for memory in manager.get_memories()]

    assert stored_ids == [
        "mem_002",
        "mem_003",
        "mem_004",
    ]


def test_manager_does_not_exceed_capacity():
    manager = MemoryManager(capacity=2)

    manager.add_memory(create_memory("mem_001", 1.0))
    manager.add_memory(create_memory("mem_002", 2.0))
    manager.add_memory(create_memory("mem_003", 3.0))

    assert len(manager) == 2


def test_get_memory():
    manager = MemoryManager(capacity=3)
    memory = create_memory("mem_001", 1.0)

    manager.add_memory(memory)

    result = manager.get_memory("mem_001")

    assert result is not None
    assert result.memory_id == "mem_001"


def test_get_missing_memory():
    manager = MemoryManager(capacity=3)

    assert manager.get_memory("missing") is None


def test_remove_memory():
    manager = MemoryManager(capacity=3)
    manager.add_memory(create_memory("mem_001", 1.0))
    manager.add_memory(create_memory("mem_002", 2.0))

    removed = manager.remove_memory("mem_001")

    assert removed is True
    assert manager.get_memory("mem_001") is None
    assert len(manager) == 1


def test_remove_missing_memory():
    manager = MemoryManager(capacity=3)

    removed = manager.remove_memory("missing")

    assert removed is False


def test_clear_memories():
    manager = MemoryManager(capacity=3)
    manager.add_memory(create_memory("mem_001", 1.0))
    manager.add_memory(create_memory("mem_002", 2.0))

    manager.clear()

    assert len(manager) == 0
    assert manager.get_memories() == []


def test_invalid_capacity():
    try:
        MemoryManager(capacity=0)
        assert False
    except ValueError:
        assert True
