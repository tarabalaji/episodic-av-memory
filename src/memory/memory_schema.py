"""Validated event and memory records. SI units: seconds, metres, metres/second."""
from dataclasses import asdict, dataclass, field
import math
from typing import Any
from urllib.parse import quote


def validate_observation(record):
    for name in ("episode_id", "event_type", "description", "weather", "road_type", "action", "outcome"):
        value = getattr(record, name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string.")
    for name in ("timestamp", "speed", "distance_to_obstacle", "time_to_collision"):
        value = getattr(record, name)
        if value is None and name in ("distance_to_obstacle", "time_to_collision"):
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative (or null for unknown distance/TTC).")


@dataclass
class RawDrivingEvent:
    event_id: str
    episode_id: str
    timestamp: float
    event_type: str
    description: str
    speed: float
    distance_to_obstacle: float | None
    time_to_collision: float | None
    weather: str
    road_type: str
    action: str
    outcome: str

    def __post_init__(self):
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError("event_id must be a nonempty string.")
        validate_observation(self)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("An event must be an object.")
        return cls(**data)


@dataclass
class DrivingMemory:
    memory_id: str
    episode_id: str
    timestamp: float
    event_type: str
    description: str
    speed: float
    distance_to_obstacle: float | None
    time_to_collision: float | None
    weather: str
    road_type: str
    action: str
    outcome: str
    importance_score: float = 0.0
    protected: bool = False
    access_count: int = 0
    source_memory_ids: list[str] = field(default_factory=list)
    occurrence_count: int = 1
    sequence_index: int = -1

    def __post_init__(self):
        validate_observation(self)
        if not isinstance(self.memory_id, str) or not self.memory_id.strip():
            raise ValueError("memory_id must be a nonempty string.")
        if not isinstance(self.importance_score, (int, float)) or isinstance(self.importance_score, bool) or not 0 <= self.importance_score <= 1:
            raise ValueError("importance_score must be between 0 and 1.")
        if type(self.protected) is not bool:
            raise ValueError("protected must be a boolean.")
        for name, minimum in (("access_count", 0), ("occurrence_count", 1), ("sequence_index", -1)):
            if type(getattr(self, name)) is not int or getattr(self, name) < minimum:
                raise ValueError(f"Invalid {name}.")
        if not isinstance(self.source_memory_ids, list) or any(not isinstance(x, str) or not x for x in self.source_memory_ids):
            raise ValueError("source_memory_ids must be a list of nonempty strings.")
        if not self.source_memory_ids:
            self.source_memory_ids = [self.memory_id]
        if len(set(self.source_memory_ids)) != len(self.source_memory_ids):
            raise ValueError("source_memory_ids must be unique.")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_event(cls, event, importance_score=0.0, protected=False):
        values = event.to_dict()
        values.pop("event_id")
        identity = f"mem_{quote(event.episode_id, safe='')}:{quote(event.event_id, safe='')}"
        return cls(memory_id=identity, importance_score=importance_score,
                   protected=protected, **values)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
