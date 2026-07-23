from src.memory.memory_schema import DrivingMemory


class CompressionStrategy:
    def __init__(
        self,
        similarity_window: float = 10.0,
    ):
        if similarity_window < 0:
            raise ValueError("similarity_window cannot be negative.")

        self.similarity_window = similarity_window

    def manage(
        self,
        memories: list[DrivingMemory],
    ) -> DrivingMemory:
        if not memories:
            raise ValueError("Cannot compress an empty memory list.")

        ordered_memories = sorted(
            memories,
            key=lambda memory: memory.timestamp,
        )

        for first_index, first in enumerate(ordered_memories):
            for second in ordered_memories[first_index + 1 :]:
                if self._similar(first, second):
                    self._merge(
                        target=first,
                        duplicate=second,
                    )

                    memories.remove(second)
                    return second

        removable_memories = [memory for memory in memories if not memory.protected]

        if not removable_memories:
            raise RuntimeError(
                "Cannot remove a memory because all memories are protected."
            )

        oldest_memory = min(
            removable_memories,
            key=lambda memory: memory.timestamp,
        )

        memories.remove(oldest_memory)
        return oldest_memory

    def _similar(
        self,
        first: DrivingMemory,
        second: DrivingMemory,
    ) -> bool:
        if first.event_type != second.event_type:
            return False

        if first.road_type != second.road_type:
            return False

        if first.weather != second.weather:
            return False

        time_difference = abs(first.timestamp - second.timestamp)

        if time_difference > self.similarity_window:
            return False

        return True

    def _merge(
        self,
        target: DrivingMemory,
        duplicate: DrivingMemory,
    ) -> None:
        target.access_count += duplicate.access_count + 1

        target.importance_score = max(
            target.importance_score,
            duplicate.importance_score,
        )

        target.timestamp = max(
            target.timestamp,
            duplicate.timestamp,
        )

        target.protected = target.protected or duplicate.protected

        if not target.description.endswith(" (repeated)"):
            target.description += " (repeated)"
