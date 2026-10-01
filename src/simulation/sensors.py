"""Own and clean up CARLA sensors; buffer asynchronous callbacks by frame."""
from collections import deque
import math
from threading import Lock


def speed(vector):
    return math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2)


def estimated_ttc(distance, ego_velocity, other_velocity, ego_location, other_location):
    """Line-of-sight constant-velocity TTC proxy; not collision ground truth."""
    delta = [getattr(other_location, axis) - getattr(ego_location, axis) for axis in ("x", "y", "z")]
    norm = math.sqrt(sum(value * value for value in delta))
    if norm == 0:
        return 0.0 if distance == 0 else None
    closing = sum((getattr(ego_velocity, axis) - getattr(other_velocity, axis)) * component / norm
                  for axis, component in zip(("x", "y", "z"), delta))
    return distance / closing if closing > 1e-6 else None


class SensorSuite:
    def __init__(self, world, vehicle, carla_module, max_age=0.5, queue_size=4096):
        if not math.isfinite(max_age) or max_age <= 0 or type(queue_size) is not int or queue_size < 1:
            raise ValueError("Sensor age and queue size must be positive.")
        self.world, self.vehicle, self.carla = world, vehicle, carla_module
        self.max_age, self.queue_size = max_age, queue_size
        self.actors, self.errors = [], []
        self.obstacles, self.collisions = deque(), deque()
        self.latest_obstacle = None
        self._lock = Lock()

    def start(self):
        if self.actors:
            raise RuntimeError("Sensors are already started.")
        try:
            library = self.world.get_blueprint_library()
            collision = self.world.spawn_actor(library.find("sensor.other.collision"),
                                               self.carla.Transform(), attach_to=self.vehicle)
            self.actors.append(collision)
            collision.listen(self._collision)
            blueprint = library.find("sensor.other.obstacle")
            blueprint.set_attribute("distance", "50")
            blueprint.set_attribute("only_dynamics", "false")
            obstacle = self.world.spawn_actor(blueprint, self.carla.Transform(), attach_to=self.vehicle)
            self.actors.append(obstacle)
            obstacle.listen(self._obstacle)
            return self
        except Exception:
            self.close()
            raise

    def _append(self, queue, value):
        with self._lock:
            if len(queue) >= self.queue_size:
                if not self.errors:
                    self.errors.append("Sensor queue overflow; recording cannot silently drop observations.")
                return
            queue.append(value)

    def _collision(self, event):
        self._append(self.collisions, (event.frame, event.timestamp))

    def _obstacle(self, event):
        try:
            ttc = estimated_ttc(event.distance, self.vehicle.get_velocity(), event.other_actor.get_velocity(),
                                self.vehicle.get_location(), event.other_actor.get_location())
            self._append(self.obstacles, (event.frame, event.timestamp, event.distance, ttc))
        except Exception as error:
            with self._lock:
                if not self.errors:
                    self.errors.append(f"Obstacle callback failed: {type(error).__name__}")

    def sample(self, frame, timestamp):
        with self._lock:
            if self.errors:
                raise RuntimeError(self.errors[0])
            eligible = [record for record in self.obstacles if record[0] <= frame]
            self.obstacles = deque(record for record in self.obstacles if record[0] > frame)
            if eligible:
                # Preserve the nearest obstacle when a frame contains several detections.
                latest_frame = max(record[0] for record in eligible)
                latest = min((r for r in eligible if r[0] == latest_frame), key=lambda r: r[2])
                if self.latest_obstacle is None or latest[0] >= self.latest_obstacle[0]:
                    self.latest_obstacle = latest
            collisions = [record for record in self.collisions if record[0] <= frame]
            self.collisions = deque(record for record in self.collisions if record[0] > frame)
            fresh = self.latest_obstacle is not None and 0 <= timestamp - self.latest_obstacle[1] <= self.max_age
            return {"distance": self.latest_obstacle[2] if fresh else None,
                    "ttc": self.latest_obstacle[3] if fresh else None,
                    "collision_events": len(collisions),
                    "sensor_timestamp": self.latest_obstacle[1] if fresh else None}

    def close(self):
        errors = []
        for actor in reversed(self.actors):
            try:
                actor.stop()
            except Exception as error:
                errors.append(error)
            try:
                actor.destroy()
            except Exception as error:
                errors.append(error)
        self.actors.clear()
        if errors:
            import warnings
            warnings.warn(f"{len(errors)} sensor cleanup operations failed.", RuntimeWarning)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
