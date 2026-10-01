"""End-to-end launcher tests use fake CARLA. No live server is contacted."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from test_carla import World, Blueprint, client_for, vector
from src.simulation.connection import normalize_host, inspect_server
from src.simulation.demo_vehicle import DemoVehicle
from src.simulation.session import run_session, run_offline_check
from scripts.start_carla import main, ask_value, port_number


class LauncherWorld(World):
    def __init__(self):
        super().__init__()
        self.synchronous = False
        self.existing = [self.vehicle]
        self.created = None
        self.occupied = False
        self.spawn_calls = 0
        self.vehicle.type_id = "vehicle.test"
        self.settings_changed = False

    def get_settings(self):
        return NS(synchronous_mode=self.synchronous, fixed_delta_seconds=.05)

    def get_actors(self):
        return NS(filter=lambda pattern: self.existing + ([self.created] if self.created else []))

    def get_map(self):
        return NS(name="TestTown", get_waypoint=lambda location: NS(is_junction=False),
                  get_spawn_points=lambda: ["point1", "point2"])

    def get_blueprint_library(self):
        blueprint = NS(id="vehicle.test", has_attribute=lambda name: True,
                       get_attribute=lambda name: "4", set_attribute=Mock())
        return NS(find=lambda name: Blueprint(), filter=lambda pattern: [blueprint])

    def try_spawn_actor(self, blueprint, transform):
        self.spawn_calls += 1
        if self.occupied:
            return None
        self.created = NS(id=99, attributes={"role_name": "asdrp_memory_demo"}, type_id="vehicle.test",
            get_velocity=lambda: vector(5), get_location=lambda: vector(),
            get_control=lambda: NS(brake=0, throttle=.2), set_autopilot=Mock(), destroy=Mock(return_value=True))
        return self.created


def setup_client():
    world = LauncherWorld()
    client, _ = client_for(world)
    client.connect()
    client.client.get_trafficmanager = Mock(return_value=NS(get_port=lambda: 8050))
    return client, world


@pytest.mark.parametrize("bad", ["", None, "http://server", "server:2000", "user@server", "server/path"])
def test_host_input_rejects_urls_and_mixed_fields(bad):
    with pytest.raises(ValueError):
        normalize_host(bad)


def test_host_input_accepts_names_and_ipv6():
    assert normalize_host("  localhost ") == "localhost"
    assert normalize_host("[::1]") == "::1"
    assert normalize_host("192.168.1.12") == "192.168.1.12"


def test_connection_check_is_read_only_and_rejects_mismatched_versions():
    client, world = setup_client()
    info = inspect_server(client)
    assert info["vehicles"][0]["id"] == 7
    assert world.spawn_calls == 0 and not world.sensors
    client.client.get_server_version = lambda: "different-version"
    with pytest.raises(RuntimeError, match="version mismatch"):
        inspect_server(client)
    assert world.spawn_calls == 0 and not world.sensors


def test_existing_vehicle_session_records_and_evaluates(tmp_path):
    client, world = setup_client()
    messages = []
    result = run_session(client, tmp_path / "existing", frames=4, vehicle_id=7,
                         capacities=[2], bootstrap_samples=100, emit=messages.append)
    output = tmp_path / "existing"
    assert json.loads((output / "run_status.json").read_text())["status"] == "complete"
    assert json.loads((output / "analysis/run_status.json").read_text())["status"] == "complete"
    assert (output / "events.jsonl").is_file()
    assert result["report"] == str(output / "analysis/comparison.html")
    assert world.spawn_calls == 0
    assert all(sensor.destroyed for sensor in world.sensors)
    assert any("4/4" in message for message in messages)
    manifest = json.loads((output / "session.json").read_text())
    assert manifest["memory_controls_vehicle"] is False
    assert manifest["independent_episodes"] == 1
    assert all(row["ci_low"] is None for row in result["metrics"])


def test_demo_vehicle_is_driven_and_destroyed(tmp_path):
    client, world = setup_client()
    world.existing = []
    result = run_session(client, tmp_path / "demo", frames=3, demo=True,
                         capacities=[2], bootstrap_samples=100, emit=lambda message: None)
    world.created.set_autopilot.assert_any_call(True, 8050)
    world.created.set_autopilot.assert_any_call(False, 8050)
    world.created.destroy.assert_called_once()
    assert not world.settings_changed
    manifest = json.loads((tmp_path / "demo/session.json").read_text())
    assert manifest["demo"]["cleanup_confirmed"] is True
    assert manifest["demo"]["deterministic_driving"] is False


def test_failure_releases_demo_vehicle_and_preserves_failed_recording(tmp_path):
    client, world = setup_client()
    world.fail_tick = True
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="timeout"):
        run_session(client, output, frames=3, demo=True, emit=lambda message: None)
    world.created.destroy.assert_called_once()
    assert all(sensor.destroyed for sensor in world.sensors)
    assert json.loads((output / "run_status.json").read_text())["status"] == "failed"
    assert not json.loads((output / "events.metadata.json").read_text())["complete"]
    assert not (output / "analysis").exists()


def test_existing_results_refused_before_spawning(tmp_path):
    client, world = setup_client()
    (tmp_path / "preserve.txt").write_text("existing result")
    with pytest.raises(FileExistsError):
        run_session(client, tmp_path, demo=True)
    assert world.spawn_calls == 0
    assert (tmp_path / "preserve.txt").read_text() == "existing result"


def test_demo_does_not_take_over_synchronous_clock(tmp_path):
    client, world = setup_client()
    world.synchronous = True
    with pytest.raises(RuntimeError, match="asynchronous"):
        run_session(client, tmp_path / "sync", demo=True)
    assert not (tmp_path / "sync").exists()
    assert world.spawn_calls == 0


def test_occupied_spawn_points_are_handled_without_hanging():
    client, world = setup_client()
    world.occupied = True
    with pytest.raises(RuntimeError, match="occupied"):
        with DemoVehicle(client):
            pytest.fail("No vehicle should be yielded")
    assert world.spawn_calls == 2


def test_autopilot_startup_failure_releases_owned_vehicle():
    client, world = setup_client()
    client.client.get_trafficmanager.side_effect = RuntimeError("Traffic Manager unavailable")
    with pytest.raises(RuntimeError, match="Traffic Manager"):
        with DemoVehicle(client):
            pytest.fail("Should fail before returning a vehicle")
    world.created.destroy.assert_called_once()


def test_read_only_cli_connects_without_creating_outputs(monkeypatch, tmp_path):
    client, world = setup_client()
    monkeypatch.setattr("src.simulation.carla_client.CarlaClient", lambda *args: client)
    messages = []
    code = main(["--host", "server", "--check", "--non-interactive", "--output", str(tmp_path / "unused")], emit=messages.append)
    assert code == 0 and not world.sensors and world.spawn_calls == 0
    assert not (tmp_path / "unused").exists()


def test_interactive_cli_accepts_server_details_and_vehicle_choice(monkeypatch, tmp_path):
    client, world = setup_client()
    factory = Mock(return_value=client)
    monkeypatch.setattr("src.simulation.carla_client.CarlaClient", factory)
    answers = iter(["my-server", "2000", "3", "7"])
    assert main(["--no-browser", "--output", str(tmp_path / "interactive")],
                ask=lambda prompt: next(answers), emit=lambda message: None) == 0
    factory.assert_called_once_with("my-server", 2000, 10.0)
    assert (tmp_path / "interactive/analysis/comparison.html").exists()


def test_missing_client_has_friendly_actionable_message(monkeypatch):
    def missing(name):
        raise ImportError("not installed")
    monkeypatch.setattr("src.simulation.carla_client.importlib.import_module", missing)
    messages = []
    code = main(["--host", "localhost", "--non-interactive", "--check"], emit=messages.append)
    assert code == 1
    assert any("compatible Windows/Linux" in message for message in messages)
    assert any("--offline" in message for message in messages)


def test_offline_cli_never_contacts_carla(monkeypatch, tmp_path):
    factory = Mock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr("src.simulation.carla_client.CarlaClient", factory)
    code = main(["--offline", "--no-browser", "--output", str(tmp_path / "offline")], emit=lambda message: None)
    assert code == 0
    factory.assert_not_called()
    assert json.loads((tmp_path / "offline/session.json").read_text())["server_contacted"] is False


def test_bad_port_prompt_retries_and_interrupt_exits(monkeypatch):
    answers = iter(["bad", "70000", "2001"])
    assert ask_value("port", 2000, port_number, lambda prompt: next(answers), lambda message: None) == 2001
    def cancel(prompt):
        raise KeyboardInterrupt
    assert main([], ask=cancel, emit=lambda message: None) == 130


def test_keyboard_interrupt_cleans_up_owned_resources(tmp_path):
    client, world = setup_client()
    def interrupted(timeout):
        raise KeyboardInterrupt
    world.wait_for_tick = interrupted
    output = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        run_session(client, output, frames=3, demo=True, emit=lambda message: None)
    world.created.destroy.assert_called_once()
    assert all(sensor.destroyed for sensor in world.sensors)
    assert json.loads((output / "run_status.json").read_text())["error_type"] == "KeyboardInterrupt"
    assert not (output / "analysis").exists()
