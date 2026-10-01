from typing import Protocol
from copy import deepcopy

from src.memory.memory_schema import DrivingMemory


class MemoryStrategy(Protocol):
    def manage(self, memories: list[DrivingMemory]) -> DrivingMemory: ...


class MemoryManager:
    def __init__(
        self,
        capacity: int,
        strategy: MemoryStrategy,
    ):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        self.capacity = capacity
        self.strategy = strategy
        self.memories: list[DrivingMemory] = []

    def add_memory(self, memory: DrivingMemory) -> None:
        if not isinstance(memory, DrivingMemory):
            raise TypeError("memory must be a DrivingMemory object.")

        if self.get_memory(memory.memory_id) is not None:
            raise ValueError(f"Duplicate memory ID: {memory.memory_id}")
        previous = list(self.memories)
        snapshots = [(item, deepcopy(item.__dict__)) for item in previous + [memory]]
        try:
            self.memories.append(memory)
            if hasattr(self.strategy, "protect_critical_memories"):
                self.strategy.protect_critical_memories(self.memories)
            while len(self.memories) > self.capacity:
                count = len(self.memories)
                self.strategy.manage(self.memories)
                if len(self.memories) >= count:
                    raise RuntimeError("Memory strategy did not reduce memory count.")
        except Exception:
            self.memories[:] = previous
            for item, state in snapshots:
                item.__dict__.clear()
                item.__dict__.update(state)
            raise

    def get_memories(self) -> list[DrivingMemory]:
        return list(self.memories)

    def get_memory(self, memory_id: str) -> DrivingMemory | None:
        for memory in self.memories:
            if memory.memory_id == memory_id:
                return memory

        return None

    def remove_memory(self, memory_id: str) -> bool:
        memory = self.get_memory(memory_id)

        if memory is None:
            return False

        self.memories.remove(memory)
        return True

    def clear(self) -> None:
        self.memories.clear()

    def set_strategy(self, strategy: MemoryStrategy) -> None:
        self.strategy = strategy

    def is_full(self) -> bool:
        return len(self.memories) >= self.capacity

    def __len__(self) -> int:
        return len(self.memories)
