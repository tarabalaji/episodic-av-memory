"""Convert observed events into scored episodic memories."""
from src.memory.memory_schema import DrivingMemory, RawDrivingEvent
from src.memory.strategies.core_safety import CoreSafetyStrategy
from src.memory.strategies.importance import ImportanceStrategy


class MemoryBuilder:
    def __init__(self, protect_critical: bool = False):
        self.protect_critical = protect_critical
        self.safety = CoreSafetyStrategy()
        self.scorer = ImportanceStrategy()

    def build(self, event: RawDrivingEvent) -> DrivingMemory:
        memory = DrivingMemory.from_event(event)
        if self.protect_critical:
            memory.protected = self.safety.is_critical(memory)
        memory.importance_score = self.scorer.calculate_score(memory, event.timestamp)
        return memory
