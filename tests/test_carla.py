"""Mocked integration tests. These do NOT constitute validation against CARLA."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from src.simulation.carla_client import CarlaClient
from src.simulation.sensors import SensorSuite, estimated_ttc
from src.simulation.data_logger import load_events


def vector(x=0, y=0, z=0):
    return NS(x=x, y=y, z=z)


class Blueprint:
    def set_attribute(self, *args):
        pass


class Sensor:
    def __init__(self):
        self.callback = None
        self.stopped = self.destroyed = False
    def listen(self, callback):
        self.callback = callback
    def stop(self):
        self.stopped = True
    def destroy(self):
        self.destroyed = True


class World:
    def __init__(self):
        self.sensors, self.frame = [], 0
        self.vehicle = NS(id=7, attributes={"role_name": "hero"},
                          get_velocity=lambda: vector(5), get_location=lambda: vector(),
                          get_control=lambda: NS(brake=0, throttle=.2))
        self.fail_tick = False
        self.fail_spawn = False
    def get_actors(self):
        return NS(filter=lambda pattern: [self.vehicle])
    def get_map(self):
        return NS(name="TestTown", get_waypoint=lambda location: NS(is_junction=False))
    def get_weather(self):
        return NS(precipitation=0, fog_density=0)
    def get_blueprint_library(self):
        return NS(find=lambda name: Blueprint())
    def spawn_actor(self, *args, **kwargs):
        if self.fail_spawn and self.sensors:
            raise RuntimeError("spawn failure")
        sensor = Sensor()
        self.sensors.append(sensor)
        return sensor
    def wait_for_tick(self, timeout):
        if self.fail_tick:
            raise RuntimeError("server timeout")
        self.frame += 1
        timestamp = self.frame / 10
        self.sensors[1].callback(NS(frame=self.frame, timestamp=timestamp, distance=10,
            other_actor=NS(get_velocity=lambda: vector(0), get_location=lambda: vector(10))))
        if self.frame == 2:
            self.sensors[0].callback(NS(frame=2, timestamp=timestamp))
        return NS(frame=self.frame, timestamp=NS(elapsed_seconds=timestamp),
                  find=lambda identity: NS(get_velocity=lambda: vector(5)))


def client_for(world):
    native = NS(set_timeout=Mock(), get_world=lambda: world,
                get_client_version=lambda: "fake", get_server_version=lambda: "fake")
    module = NS(Client=lambda host, port: native, Transform=lambda: object())
    return CarlaClient(carla_module=module), module


def test_mocked_carla_recording_roundtrip_and_cleanup(tmp_path):
    world = World()
    client, _ = client_for(world)
    output = tmp_path / "carla.jsonl"
    metadata = client.record(output, frames=3, episode_id="test")
    events = load_events(output)
    assert len(events) == 3 and metadata["complete"]
    assert events[0].speed == 5 and events[0].time_to_collision == 2
    assert events[1].outcome == "collision" and events[1].event_type == "collision"
    assert events[2].outcome == "unlabeled"
    assert metadata["collision_callbacks"] == 1
    assert all(sensor.stopped and sensor.destroyed for sensor in world.sensors)
    assert json.loads(output.with_suffix(".metadata.json").read_text()) == metadata
    with pytest.raises(FileExistsError):
        client.record(output, frames=1)


def test_server_failure_cleans_up_and_marks_incomplete(tmp_path):
    world = World()
    world.fail_tick = True
    client, _ = client_for(world)
    output = tmp_path / "failed.jsonl"
    with pytest.raises(RuntimeError, match="timeout"):
        client.record(output, 3)
    assert all(sensor.destroyed for sensor in world.sensors)
    assert not json.loads(output.with_suffix(".metadata.json").read_text())["complete"]


def test_partial_sensor_startup_cleans_up(tmp_path):
    world = World()
    world.fail_spawn = True
    client, _ = client_for(world)
    with pytest.raises(RuntimeError, match="spawn failure"):
        client.record(tmp_path / "failed.jsonl", 3)
    assert world.sensors[0].destroyed


def test_sensor_future_frame_staleness_and_overflow():
    world = World()
    _, module = client_for(world)
    suite = SensorSuite(world, world.vehicle, module, queue_size=1)
    suite._append(suite.obstacles, (5, .5, 10, 2))
    assert suite.sample(4, .4)["distance"] is None
    assert suite.sample(5, .5)["distance"] == 10
    assert suite.sample(20, 2)["distance"] is None
    suite._collision(NS(frame=20, timestamp=2))
    suite._collision(NS(frame=21, timestamp=2.1))
    with pytest.raises(RuntimeError, match="overflow"):
        suite.sample(21, 2.1)


def test_ttc_does_not_confuse_receding_actor_with_imminent_collision():
    assert estimated_ttc(10, vector(5), vector(10), vector(), vector(10)) is None
    assert estimated_ttc(10, vector(5), vector(), vector(), vector(10)) == 2


def test_carla_optional_dependency_error_is_actionable(monkeypatch):
    def missing(name):
        raise ImportError("no carla")
    monkeypatch.setattr("src.simulation.carla_client.importlib.import_module", missing)
    with pytest.raises(RuntimeError, match="offline pipeline needs neither"):
        CarlaClient().connect()
