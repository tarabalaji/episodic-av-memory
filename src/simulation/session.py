"""One workflow from a CARLA connection to a saved strategy comparison."""
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from src.evaluation.experiments import evaluate
from src.evaluation.output import experiment_directory
from src.simulation.connection import inspect_server
from src.simulation.data_logger import load_events
from src.simulation.demo_vehicle import DemoVehicle
from src.utils.helpers import PROJECT_ROOT, write_json


def new_output_path():
    name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    return PROJECT_ROOT / "data/results" / f"carla_{name}"


def run_session(client, output_dir=None, *, frames=300, vehicle_id=None, demo=False,
                capacities=(5, 15, 30), top_k=3, traffic_manager_port=8050,
                seed=42, bootstrap_samples=2000, emit=print):
    """Live recording is one episode; do not invent independent trials by slicing it."""
    if type(frames) is not int or frames < 1:
        raise ValueError("Frames must be a positive integer.")
    capacities = list(capacities)
    if not capacities or any(type(c) is not int or c < 1 for c in capacities) or len(set(capacities)) != len(capacities):
        raise ValueError("Memory capacities must be distinct positive integers.")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    if type(bootstrap_samples) is not int or bootstrap_samples < 100:
        raise ValueError("bootstrap_samples must be at least 100.")
    if type(seed) is not int:
        raise ValueError("seed must be an integer.")
    if demo and vehicle_id is not None:
        raise ValueError("Choose a demo vehicle or an existing vehicle ID, not both.")
    info = inspect_server(client)
    if demo and info["synchronous_mode"]:
        raise RuntimeError("Demo mode requires an asynchronous server; record an existing scenario instead.")
    owner = DemoVehicle(client, traffic_manager_port, seed) if demo else None
    existing = None if demo else client.find_vehicle(vehicle_id)
    output_dir = Path(output_dir) if output_dir is not None else new_output_path()
    with experiment_directory(output_dir) as output:
        manifest = {"server": info, "mode": "autopilot_demo" if demo else "existing_vehicle",
                    "frames_requested": frames, "capacities": capacities, "top_k": top_k,
                    "seed": seed, "memory_controls_vehicle": False}
        write_json(output / "session.json", manifest)
        context = owner if owner is not None else nullcontext(existing)
        try:
            with context as vehicle:
                manifest["vehicle_id"] = vehicle.id
                write_json(output / "session.json", manifest)
                emit(f"Recording vehicle {vehicle.id}: {frames} observed frames.")
                def progress(done, total):
                    if done == total or done % max(1, total // 10) == 0:
                        emit(f"Recorded {done}/{total} frames.")
                metadata = client.record(output / "events.jsonl", frames=frames, vehicle_id=vehicle.id,
                                         on_progress=progress)
                if not metadata.get("complete") or metadata.get("frames_recorded") != frames:
                    raise RuntimeError("Recording is incomplete; comparison was not started.")
        finally:
            if owner is not None:
                manifest["demo"] = owner.metadata
                write_json(output / "session.json", manifest)
        # Sensors and any owned vehicle have been released before doing offline work.
        events = load_events(output / "events.jsonl")
        if len(events) != frames:
            raise RuntimeError("Saved event count does not match the completed recording.")
        emit("Recording saved. Comparing memory strategies locally...")
        comparison = evaluate(events, output / "analysis", capacities=capacities,
                              top_k=top_k, seed=seed, bootstrap_samples=bootstrap_samples,
                              data_kind="recorded")
        manifest["analysis_report"] = "analysis/comparison.html"
        manifest["recording_metadata"] = "events.metadata.json"
        manifest["independent_episodes"] = 1
        write_json(output / "session.json", manifest)
        emit("Finished. This is one recording, so it does not provide multi-episode confidence intervals.")
    return {"output_dir": str(output_dir.resolve()),
            "report": str((output_dir / "analysis/comparison.html").resolve()),
            "metrics": comparison["summary"]}


def run_offline_check(output_dir=None, emit=print):
    """Exercise the launcher-to-report path without claiming a CARLA connection."""
    output_dir = Path(output_dir) if output_dir is not None else new_output_path()
    with experiment_directory(output_dir) as output:
        emit("OFFLINE CHECK: using bundled sample events; no CARLA server is contacted.")
        write_json(output / "session.json", {"mode": "offline_sample", "server_contacted": False})
        events = load_events(PROJECT_ROOT / "data/raw/sample_events.json")
        evaluate(events, output / "analysis", capacities=(2, 5, 10), data_kind="unspecified")
    return {"output_dir": str(output_dir.resolve()),
            "report": str((output_dir / "analysis/comparison.html").resolve())}
