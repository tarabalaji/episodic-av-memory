from src.memory.memory_schema import DrivingMemory


class FIFOStrategy:
    def manage(self, memories: list[DrivingMemory]) -> DrivingMemory:
        if not memories:
            raise ValueError("Cannot remove a memory from an empty list.")

        return memories.pop(0)
