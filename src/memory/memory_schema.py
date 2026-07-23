from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DrivingMemory:
    memory_id: str
    episode_id: str
    timestamp: float
    event_type: str
    description: str
    speed: float
    distance_to_obstacle: float
    time_to_collision: float
    weather: str
    road_type: str
    action: str
    outcome: str
    importance_score: float = 0.0
    protected: bool = False
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrivingMemory":
        return cls(
            memory_id=str(data["memory_id"]),
            episode_id=str(data.get("episode_id", "unknown_episode")),
            timestamp=float(data["timestamp"]),
            event_type=str(data["event_type"]),
            description=str(data["description"]),
            speed=float(data["speed"]),
            distance_to_obstacle=float(data["distance_to_obstacle"]),
            time_to_collision=float(data["time_to_collision"]),
            weather=str(data["weather"]),
            road_type=str(data["road_type"]),
            action=str(data["action"]),
            outcome=str(data["outcome"]),
            importance_score=float(data.get("importance_score", 0.0)),
            protected=bool(data.get("protected", False)),
            access_count=int(data.get("access_count", 0)),
        )
