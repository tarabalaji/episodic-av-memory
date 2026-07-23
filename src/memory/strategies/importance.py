from src.memory.memory_schema import DrivingMemory


class ImportanceStrategy:
    CRITICAL_EVENT_TYPES = {
        "collision",
        "near_collision",
        "pedestrian_crossing",
        "emergency_vehicle",
    }

    CRITICAL_OUTCOMES = {
        "collision",
        "failure",
        "unsafe",
    }

    CRITICAL_ACTIONS = {
        "hard_brake",
        "emergency_brake",
        "emergency_steer",
    }

    def manage(
        self,
        memories: list[DrivingMemory],
    ) -> DrivingMemory:
        if not memories:
            raise ValueError("Cannot remove a memory from an empty list.")

        removable_memories = [memory for memory in memories if not memory.protected]

        if not removable_memories:
            raise RuntimeError(
                "Cannot remove a memory because all memories are protected."
            )

        current_time = max(memory.timestamp for memory in memories)

        for memory in memories:
            memory.importance_score = self.calculate_score(
                memory=memory,
                current_time=current_time,
            )

        least_important = min(
            removable_memories,
            key=lambda memory: (
                memory.importance_score,
                memory.timestamp,
            ),
        )

        memories.remove(least_important)
        return least_important

    def calculate_score(
        self,
        memory: DrivingMemory,
        current_time: float,
    ) -> float:
        severity_score = self._calculate_severity(memory)
        urgency_score = self._calculate_urgency(memory)
        outcome_score = self._calculate_outcome(memory)
        access_score = self._calculate_access(memory)
        recency_score = self._calculate_recency(
            memory=memory,
            current_time=current_time,
        )

        score = (
            0.30 * severity_score
            + 0.25 * urgency_score
            + 0.20 * outcome_score
            + 0.10 * access_score
            + 0.15 * recency_score
        )

        if memory.protected:
            score = 1.0

        return round(self._clamp(score), 4)

    def _calculate_severity(
        self,
        memory: DrivingMemory,
    ) -> float:
        score = 0.0

        if memory.event_type in self.CRITICAL_EVENT_TYPES:
            score += 0.7

        if memory.action in self.CRITICAL_ACTIONS:
            score += 0.3

        return self._clamp(score)

    def _calculate_urgency(
        self,
        memory: DrivingMemory,
    ) -> float:
        ttc_score = 0.0
        distance_score = 0.0

        if memory.time_to_collision is not None:
            if memory.time_to_collision <= 0.5:
                ttc_score = 1.0
            elif memory.time_to_collision <= 1.0:
                ttc_score = 0.8
            elif memory.time_to_collision <= 2.0:
                ttc_score = 0.6
            elif memory.time_to_collision <= 4.0:
                ttc_score = 0.3

        if memory.distance_to_obstacle is not None:
            if memory.distance_to_obstacle <= 1.0:
                distance_score = 1.0
            elif memory.distance_to_obstacle <= 3.0:
                distance_score = 0.8
            elif memory.distance_to_obstacle <= 7.0:
                distance_score = 0.5
            elif memory.distance_to_obstacle <= 15.0:
                distance_score = 0.2

        return max(ttc_score, distance_score)

    def _calculate_outcome(
        self,
        memory: DrivingMemory,
    ) -> float:
        if memory.outcome in self.CRITICAL_OUTCOMES:
            return 1.0

        if memory.outcome == "collision_avoided":
            return 0.8

        if memory.outcome == "successful":
            return 0.3

        return 0.5

    def _calculate_access(
        self,
        memory: DrivingMemory,
    ) -> float:
        return self._clamp(memory.access_count / 10.0)

    def _calculate_recency(
        self,
        memory: DrivingMemory,
        current_time: float,
    ) -> float:
        age = max(current_time - memory.timestamp, 0.0)

        return 1.0 / (1.0 + age)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(value, 1.0))
