import math
from src.memory.errors import MemoryCapacityError
from src.memory.memory_schema import DrivingMemory


class CompressionStrategy:
    def __init__(
        self,
        similarity_window: float = 10.0,
    ):
        if not math.isfinite(similarity_window) or similarity_window < 0:
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
            key=lambda memory: memory.sequence_index if memory.sequence_index >= 0 else memory.timestamp,
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
            raise MemoryCapacityError(
                "Cannot remove a memory because all memories are protected."
            )

        oldest_memory = min(
            removable_memories,
            key=lambda memory: memory.sequence_index if memory.sequence_index >= 0 else memory.timestamp,
        )

        memories.remove(oldest_memory)
        return oldest_memory

    def _similar(
        self,
        first: DrivingMemory,
        second: DrivingMemory,
    ) -> bool:
        if first.episode_id != second.episode_id or first.action != second.action or first.outcome != second.outcome:
            return False
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
        target.access_count += duplicate.access_count
        target.occurrence_count += duplicate.occurrence_count
        target.source_memory_ids = list(dict.fromkeys(target.source_memory_ids + duplicate.source_memory_ids))
        target.sequence_index = max(target.sequence_index, duplicate.sequence_index)
        target.speed = max(target.speed, duplicate.speed)
        for name in ("distance_to_obstacle", "time_to_collision"):
            values = [getattr(m, name) for m in (target, duplicate) if getattr(m, name) is not None]
            setattr(target, name, min(values) if values else None)

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
