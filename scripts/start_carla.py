"""Guided CARLA connection, recording, and analysis. Run with no arguments for prompts."""
import argparse
import platform
from pathlib import Path
import sys
import webbrowser
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def ask_value(prompt, default, parser, ask=input, emit=print):
    while True:
        value = ask(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
        value = value if value else default
        try:
            return parser(value)
        except (TypeError, ValueError) as error:
            emit(str(error))


def positive(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("Enter a positive whole number.") from None
    if value < 1:
        raise ValueError("Enter a positive whole number.")
    return value


def port_number(value):
    value = positive(value)
    if value > 65535:
        raise ValueError("Port must be between 1 and 65535.")
    return value


def main(argv=None, *, ask=None, emit=print):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="Server IP or hostname; omit to be prompted.")
    parser.add_argument("--port", type=port_number, help="Server port; default prompt is 2000.")
    parser.add_argument("--frames", type=positive, help="Number of observed frames; default is 300.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--vehicle-id", type=positive)
    mode.add_argument("--demo", action="store_true", help="Spawn and clean up one CARLA autopilot vehicle.")
    parser.add_argument("--traffic-manager-port", type=port_number, default=8050)
    parser.add_argument("--output", type=Path, help="Fresh output directory; generated automatically by default.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--capacities", type=positive, nargs="+", default=[5, 15, 30])
    parser.add_argument("--check", action="store_true", help="Read-only server check: no recording or vehicle creation.")
    parser.add_argument("--offline", action="store_true", help="Test the report workflow with sample data, without CARLA.")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--non-interactive", action="store_true", help="Require --host and --vehicle-id or --demo.")
    parser.add_argument("--debug", action="store_true", help="Show a full traceback for troubleshooting.")
    args = parser.parse_args(argv)
    ask = input if ask is None else ask
    try:
        # Delayed imports allow --help to work even before dependencies are installed.
        from src.simulation.carla_client import CarlaClient
        from src.simulation.connection import inspect_server, normalize_host
        from src.simulation.session import run_session, run_offline_check
        if args.offline:
            if args.check or args.demo or args.vehicle_id is not None or args.host is not None or args.port is not None:
                raise ValueError("Use --offline by itself with optional --output/--no-browser; it does not connect to a server.")
            result = run_offline_check(args.output, emit)
        else:
            if args.non_interactive and not args.host:
                raise ValueError("Non-interactive runs require --host.")
            host = normalize_host(args.host) if args.host else ask_value("CARLA server IP or hostname", "localhost", normalize_host, ask, emit)
            port = args.port or (2000 if args.non_interactive else ask_value("Server port", 2000, port_number, ask, emit))
            emit(f"Connecting to {host}:{port}...")
            client = CarlaClient(host, port, args.timeout)
            info = inspect_server(client)
            emit(f"Connected: CARLA {info['server_version']}, map {info['map']}.")
            if info["synchronous_mode"]:
                emit("This server uses a synchronous clock. Its existing scenario controller must keep advancing it.")
            for vehicle in info["vehicles"]:
                emit(f"Vehicle {vehicle['id']}: {vehicle['type']} (role: {vehicle['role'] or 'none'})")
            if args.check:
                emit("Connection check complete. No vehicle or world settings were changed.")
                return 0
            frames = args.frames or (300 if args.non_interactive else ask_value("Frames to record (300 is a short test)", 300, positive, ask, emit))
            demo, vehicle_id = args.demo, args.vehicle_id
            if not demo and vehicle_id is None:
                if args.non_interactive:
                    raise ValueError("Choose --vehicle-id ID or --demo for a non-interactive run.")
                preferred = [v for v in info["vehicles"] if v["role"] in ("hero", "ego")]
                default = str(preferred[0]["id"]) if len(preferred) == 1 else (
                    str(info["vehicles"][0]["id"]) if len(info["vehicles"]) == 1 else ("demo" if not info["vehicles"] else None))
                ids = {v["id"] for v in info["vehicles"]}
                def vehicle_choice(value):
                    if value == "demo":
                        if info["synchronous_mode"]:
                            raise ValueError("Demo mode needs an asynchronous server; select an existing vehicle ID.")
                        return "demo"
                    identity = positive(value)
                    if identity not in ids:
                        raise ValueError("Choose one of the listed vehicle IDs, or type demo to create a new autopilot vehicle.")
                    return identity
                if not ids and info["synchronous_mode"]:
                    raise RuntimeError("No vehicle is available, and the server is synchronous. Start a scenario with a vehicle/controller, or use a default asynchronous server for a demo.")
                choice = ask_value("Vehicle ID, or 'demo' to create an autopilot vehicle", default, vehicle_choice, ask, emit)
                demo, vehicle_id = (True, None) if choice == "demo" else (False, choice)
            result = run_session(client, args.output, frames=frames, vehicle_id=vehicle_id, demo=demo,
                                 capacities=args.capacities, traffic_manager_port=args.traffic_manager_port, emit=emit)
        emit(f"Results saved: {result['output_dir']}")
        emit(f"Open this report: {result['report']}")
        if not args.no_browser:
            try:
                if not webbrowser.open(Path(result["report"]).as_uri()):
                    emit("A browser could not be opened here. Open the saved HTML report on your computer.")
            except (OSError, webbrowser.Error):
                emit("Open the saved HTML report manually on your computer.")
        return 0
    except (KeyboardInterrupt, EOFError):
        emit("Stopped. Any partial recording is preserved; sensors and owned demo vehicles are cleaned up when reachable.")
        return 130
    except Exception as error:
        if args.debug:
            raise
        emit(f"Could not finish: {error}")
        if isinstance(error, ModuleNotFoundError):
            emit("Install the project dependencies first: python -m pip install -r requirements-lock.txt")
        if "CARLA is optional" in str(error):
            emit(f"Current environment: {platform.system()} {platform.machine()}, Python {platform.python_version()}.")
            emit("Run this launcher on a CARLA-compatible Windows/Linux machine with the matching Python client. "
                 "For CARLA 0.9.16, this project's compatible documented Python range is 3.11–3.12. "
                 "A server address alone cannot install the simulator or make a missing/incompatible client work.")
            emit("Once using compatible Python: python -m pip install carla==YOUR_SERVER_VERSION")
            emit("You can test this workflow now without CARLA: python -m scripts.start_carla --offline")
        elif "timeout" in str(error).lower() or "time-out" in str(error).lower() or "connect" in str(error).lower():
            emit("Check that CARLA is running, the hostname/port are correct, and the server's RPC and streaming ports "
                 "(normally 2000/2001) are reachable. Synchronous servers need a scenario client advancing the clock.")
        emit("Use --debug for details. Existing completed results are preserved.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
