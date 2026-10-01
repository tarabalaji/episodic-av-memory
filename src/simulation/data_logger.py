"""Read JSON arrays or append-only JSONL event logs."""
import json
from pathlib import Path
from threading import Lock
from src.memory.memory_schema import RawDrivingEvent
from src.utils.helpers import loads_json


def load_events(path) -> list[RawDrivingEvent]:
    path = Path(path)
    with path.open(encoding="utf-8") as stream:
        if path.suffix == ".jsonl":
            rows = [loads_json(line) for line in stream if line.strip()]
        else:
            rows = loads_json(stream.read())
    if not isinstance(rows, list):
        raise ValueError("Event file must contain a JSON array or JSONL records.")
    events, seen, timestamps = [], set(), {}
    for index, row in enumerate(rows):
        try:
            event = RawDrivingEvent.from_dict(row)
            identity = (event.episode_id, event.event_id)
            if identity in seen:
                raise ValueError(f"Duplicate event ID {identity}.")
            if event.timestamp < timestamps.get(event.episode_id, -1):
                raise ValueError("Timestamps must be ordered within each episode.")
            seen.add(identity)
            timestamps[event.episode_id] = event.timestamp
            events.append(event)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid event at record {index + 1}: {error}") from error
    return events


class DataLogger:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.suffix != ".jsonl":
            raise ValueError("Append-only event logs must use the .jsonl extension.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log(self, event: RawDrivingEvent):
        line = json.dumps(event.to_dict(), allow_nan=False)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def validate_event_sequence(events):
    """Validate an entire replay before producing plans or writing experiment output."""
    events = list(events)
    seen, times = set(), {}
    for event in events:
        if not isinstance(event, RawDrivingEvent):
            raise ValueError("Replay inputs must be RawDrivingEvent records.")
        event.__post_init__()
        identity = (event.episode_id, event.event_id)
        if identity in seen or event.timestamp < times.get(event.episode_id, -1):
            raise ValueError("Events need unique episode/event IDs and ordered episode timestamps.")
        seen.add(identity)
        times[event.episode_id] = event.timestamp
    return events
