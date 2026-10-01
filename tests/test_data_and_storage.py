import json
import sqlite3
import pytest
from src.memory.memory_schema import RawDrivingEvent, DrivingMemory
from src.memory.memory_database import MemoryDatabase
from src.memory.memory_builder import MemoryBuilder
from src.simulation.data_logger import DataLogger, load_events
from src.utils.helpers import write_json


@pytest.mark.parametrize("field,value", [("speed", -1), ("speed", True), ("timestamp", float("nan")),
    ("time_to_collision", float("inf")), ("distance_to_obstacle", -1), ("episode_id", None),
    ("event_id", ""), ("description", ""), ("weather", 4)])
def test_invalid_data_rejected(field, value, event_factory):
    data = event_factory().to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        RawDrivingEvent.from_dict(data)


def test_unknown_sensor_values_roundtrip(event_factory):
    event = event_factory(time_to_collision=None, distance_to_obstacle=None)
    memory = MemoryBuilder().build(event)
    assert DrivingMemory.from_dict(memory.to_dict()) == memory


def test_jsonl_log_roundtrip_and_duplicate_detection(tmp_path, event_factory):
    path = tmp_path / "events.jsonl"
    logger = DataLogger(path)
    events = [event_factory(i) for i in range(4)]
    for event in events:
        logger.log(event)
    assert load_events(path) == events
    logger.log(events[0])
    with pytest.raises(ValueError, match="record 5"):
        load_events(path)


def test_database_failed_replacement_keeps_existing_snapshot(tmp_path, event_factory):
    memory = MemoryBuilder().build(event_factory())
    with MemoryDatabase(tmp_path / "memories.db") as database:
        database.save([memory])
        with pytest.raises(sqlite3.IntegrityError):
            database.save([memory, memory])
        assert database.load() == [memory]
        database.save([])
        assert database.load() == []


def test_atomic_json_failure_preserves_previous_file(tmp_path):
    path = tmp_path / "output.json"
    write_json(path, {"valid": 1})
    with pytest.raises(ValueError):
        write_json(path, {"invalid": float("nan")})
    assert json.loads(path.read_text()) == {"valid": 1}
    assert list(tmp_path.iterdir()) == [path]
