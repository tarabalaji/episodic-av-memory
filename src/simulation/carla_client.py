"""Optional passive CARLA recorder. Importing this module does not require CARLA."""
from datetime import datetime, timezone
import importlib
from pathlib import Path
import math
from uuid import uuid4
from src.memory.memory_schema import RawDrivingEvent
from src.simulation.data_logger import DataLogger
from src.simulation.connection import normalize_host
from src.simulation.sensors import SensorSuite, speed
from src.utils.helpers import write_json


class CarlaClient:
    def __init__(self, host="localhost", port=2000, timeout=10.0, carla_module=None):
        if not math.isfinite(timeout) or timeout <= 0 or type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid CARLA timeout or port.")
        self.host, self.port, self.timeout = normalize_host(host), port, timeout
        self.carla = carla_module
        self.client = self.world = None

    def connect(self):
        if self.carla is None:
            try:
                self.carla = importlib.import_module("carla")
            except ImportError as error:
                raise RuntimeError("CARLA is optional. Install the Python client matching your simulator and Python version to record live data; the offline pipeline needs neither.") from error
        self.client = self.carla.Client(self.host, self.port)
        self.client.set_timeout(self.timeout)
        self.world = self.client.get_world()
        return self

    def find_vehicle(self, vehicle_id=None):
        if self.world is None:
            raise RuntimeError("Connect before selecting a vehicle.")
        vehicles = list(self.world.get_actors().filter("vehicle.*"))
        selected = [v for v in vehicles if v.id == vehicle_id] if vehicle_id is not None else [
            v for v in vehicles if v.attributes.get("role_name") in ("hero", "ego")]
        if len(selected) != 1:
            raise ValueError("Specify --vehicle-id for one existing vehicle, or create exactly one hero/ego vehicle.")
        return selected[0]

    def record(self, output, frames=300, vehicle_id=None, episode_id=None, on_progress=None):
        if type(frames) is not int or frames < 1:
            raise ValueError("frames must be a positive integer.")
        if self.world is None:
            self.connect()
        vehicle = self.find_vehicle(vehicle_id)
        output = Path(output)
        if output.suffix != ".jsonl":
            raise ValueError("CARLA recording output must end in .jsonl.")
        logger = DataLogger(output)
        output.touch(exist_ok=False)
        episode_id = episode_id or f"carla_{uuid4().hex}"
        metadata = {"episode_id": episode_id, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "map": self.world.get_map().name, "vehicle_id": vehicle.id,
                    "client_version": self.client.get_client_version(),
                    "server_version": self.client.get_server_version(),
                    "mode": "passive_recording", "frames_requested": frames, "frames_recorded": 0,
                    "complete": False, "collision_callbacks": 0,
                    "limitations": ["TTC is a constant-velocity line-of-sight estimate.",
                        "Sensor callbacks can arrive after their frame and are observed at the next sample.",
                        "Obstacle readings older than 0.5 simulation seconds are discarded.",
                        "Collision callbacks count contacts, not independent crashes.",
                        "No-collision samples have unlabeled outcomes, not assumed success.",
                        "This recorder neither controls traffic nor seeds the simulation."]}
        try:
            with SensorSuite(self.world, vehicle, self.carla) as sensors:
                previous_frame = -1
                for index in range(frames):
                    snapshot = self.world.wait_for_tick(self.timeout)
                    if snapshot is None or snapshot.frame <= previous_frame:
                        raise RuntimeError("CARLA did not deliver a new world tick.")
                    previous_frame = snapshot.frame
                    timestamp = snapshot.timestamp.elapsed_seconds
                    sample = sensors.sample(snapshot.frame, timestamp)
                    actor_snapshot = snapshot.find(vehicle.id)
                    if actor_snapshot is None:
                        raise RuntimeError("Selected vehicle disappeared during recording.")
                    velocity = speed(actor_snapshot.get_velocity())
                    weather = self.world.get_weather()
                    weather_label = "rain" if weather.precipitation > 10 else ("fog" if weather.fog_density > 20 else "clear")
                    waypoint = self.world.get_map().get_waypoint(vehicle.get_location())
                    road = "intersection" if waypoint is not None and waypoint.is_junction else "unknown"
                    control = vehicle.get_control()
                    action = "brake" if control.brake > .1 else ("accelerate" if control.throttle > .1 else "maintain")
                    collision = sample["collision_events"] > 0
                    kind = "collision" if collision else ("obstacle_detected" if sample["distance"] is not None else "normal_driving")
                    event = RawDrivingEvent(str(snapshot.frame), episode_id, timestamp, kind,
                        f"CARLA frame {snapshot.frame}: {kind}.", velocity,
                        sample["distance"], sample["ttc"], weather_label, road, action,
                        "collision" if collision else "unlabeled")
                    logger.log(event)
                    metadata["frames_recorded"] += 1
                    metadata["collision_callbacks"] += sample["collision_events"]
                    if on_progress is not None:
                        on_progress(index + 1, frames)
                metadata["complete"] = True
        finally:
            write_json(output.with_suffix(".metadata.json"), metadata)
        return metadata
