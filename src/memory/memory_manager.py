from collections import deque

from src.memory.memory_schema import DrivingMemory


class MemoryManager:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")

        self.capacity = capacity
        self.memories: deque[DrivingMemory] = deque()

    def add_memory(self, memory: DrivingMemory) -> None:
        self.memories.append(memory)

        if len(self.memories) > self.capacity:
            self.memories.popleft()

    def get_memories(self) -> list[DrivingMemory]:
        return list(self.memories)

    def get_memory(self, memory_id: str) -> DrivingMemory | None:
        for memory in self.memories:
            if memory.memory_id == memory_id:
                return memory

        return None

    def remove_memory(self, memory_id: str) -> bool:
        for memory in self.memories:
            if memory.memory_id == memory_id:
                self.memories.remove(memory)
                return True

        return False

    def clear(self) -> None:
        self.memories.clear()

    def __len__(self) -> int:
        return len(self.memories)
