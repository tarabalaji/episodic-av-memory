from typing import Protocol

from src.memory.memory_schema import DrivingMemory


class MemoryStrategy(Protocol):
    def manage(self, memories: list[DrivingMemory]) -> DrivingMemory: ...


class MemoryManager:
    def __init__(
        self,
        capacity: int,
        strategy: MemoryStrategy,
    ):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        self.capacity = capacity
        self.strategy = strategy
        self.memories: list[DrivingMemory] = []

    def add_memory(self, memory: DrivingMemory) -> None:
        if not isinstance(memory, DrivingMemory):
            raise TypeError("memory must be a DrivingMemory object.")

        self.memories.append(memory)

        while len(self.memories) > self.capacity:
            self.strategy.manage(self.memories)

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
