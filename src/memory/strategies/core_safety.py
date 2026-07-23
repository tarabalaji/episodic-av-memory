from src.memory.memory_schema import DrivingMemory


class CoreSafetyStrategy:
    CRITICAL_EVENT_TYPES = {
        "collision",
        "near_collision",
        "pedestrian_crossing",
        "emergency_vehicle",
        "vehicle_cut_in",
        "road_obstacle",
    }

    CRITICAL_OUTCOMES = {
        "collision",
        "failure",
        "unsafe",
    }

    CRITICAL_ACTIONS = {
        "emergency_brake",
        "emergency_steer",
    }

    def __init__(
        self,
        critical_ttc: float = 0.5,
        critical_distance: float = 1.0,
    ):
        if critical_ttc < 0:
            raise ValueError("critical_ttc cannot be negative.")

        if critical_distance < 0:
            raise ValueError("critical_distance cannot be negative.")

        self.critical_ttc = critical_ttc
        self.critical_distance = critical_distance

    def is_critical(
        self,
        memory: DrivingMemory,
    ) -> bool:
        if memory.event_type in self.CRITICAL_EVENT_TYPES:
            return True

        if memory.outcome in self.CRITICAL_OUTCOMES:
            return True

        if memory.action in self.CRITICAL_ACTIONS:
            return True

        if (
            memory.time_to_collision is not None
            and 0.0 <= memory.time_to_collision <= self.critical_ttc
        ):
            return True

        if (
            memory.distance_to_obstacle is not None
            and 0.0 <= memory.distance_to_obstacle <= self.critical_distance
        ):
            return True

        return False

    def protect_critical_memories(
        self,
        memories: list[DrivingMemory],
    ) -> None:
        for memory in memories:
            if self.is_critical(memory):
                memory.protected = True

    def manage(
        self,
        memories: list[DrivingMemory],
    ) -> DrivingMemory:
        if not memories:
            raise ValueError("Cannot remove a memory from an empty list.")

        self.protect_critical_memories(memories)

        removable_memories = [memory for memory in memories if not memory.protected]

        if not removable_memories:
            raise RuntimeError(
                "Cannot remove a memory because all memories are protected."
            )

        oldest_removable = min(
            removable_memories,
            key=lambda memory: memory.timestamp,
        )

        memories.remove(oldest_removable)
        return oldest_removable
