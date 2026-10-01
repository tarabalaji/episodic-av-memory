"""Optional, owned autopilot vehicle for a quick end-to-end integration check."""
import random
import warnings


class DemoVehicle:
    """Never modify existing vehicles, map, weather, or the world's clock mode.

    This demo requires an asynchronous world. A synchronous scenario should use
    the existing-vehicle recorder with its existing clock-driving client.
    """
    def __init__(self, client, traffic_manager_port=8050, seed=42):
        if type(traffic_manager_port) is not int or not 1 <= traffic_manager_port <= 65535:
            raise ValueError("Traffic Manager port must be an integer between 1 and 65535.")
        self.client = client
        self.traffic_manager_port = traffic_manager_port
        self.seed = seed
        self.vehicle = None
        self.metadata = {"driver": "CARLA Traffic Manager", "owned_vehicle": True,
                         "spawn_order_seed": seed, "traffic_manager_port": traffic_manager_port,
                         "deterministic_driving": False}

    def __enter__(self):
        world = self.client.world
        if world.get_settings().synchronous_mode:
            raise RuntimeError("The demo needs an asynchronous CARLA world. Use an existing vehicle with its scenario controller, "
                               "or start a separate default asynchronous server for this demo.")
        blueprints = [bp for bp in world.get_blueprint_library().filter("vehicle.*")
                      if bp.has_attribute("number_of_wheels") and int(bp.get_attribute("number_of_wheels")) == 4]
        blueprints.sort(key=lambda blueprint: blueprint.id)
        spawn_points = list(world.get_map().get_spawn_points())
        if not blueprints or not spawn_points:
            raise RuntimeError("This map has no suitable vehicle blueprint or spawn point.")
        random.Random(self.seed).shuffle(spawn_points)
        blueprint = blueprints[0]
        blueprint.set_attribute("role_name", "asdrp_memory_demo")
        try:
            # CARLA returns None for an occupied spawn point; try each point once.
            for transform in spawn_points:
                self.vehicle = world.try_spawn_actor(blueprint, transform)
                if self.vehicle is not None:
                    break
            if self.vehicle is None:
                raise RuntimeError("All vehicle spawn points are occupied. Free one or record an existing vehicle.")
            manager = self.client.client.get_trafficmanager(self.traffic_manager_port)
            self.vehicle.set_autopilot(True, manager.get_port())
            self.metadata.update({"vehicle_id": self.vehicle.id, "blueprint": blueprint.id})
            return self.vehicle
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.vehicle is None:
            return
        vehicle, self.vehicle = self.vehicle, None
        errors = []
        try:
            vehicle.set_autopilot(False, self.traffic_manager_port)
        except Exception as error:
            errors.append(str(error))
        try:
            if vehicle.destroy() is False:
                errors.append("Server did not confirm vehicle destruction.")
        except Exception as error:
            errors.append(str(error))
        if errors:
            warnings.warn(f"Demo vehicle {vehicle.id} cleanup needs checking: {'; '.join(errors)}", RuntimeWarning)
            self.metadata["cleanup_confirmed"] = False
            self.metadata["cleanup_errors"] = errors
        else:
            self.metadata["cleanup_confirmed"] = True

    def __exit__(self, *args):
        self.close()
