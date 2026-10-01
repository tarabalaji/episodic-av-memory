"""Record an existing vehicle on a local or remote CARLA server."""
import argparse
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.simulation.carla_client import CarlaClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--vehicle-id", type=int)
    parser.add_argument("--episode-id")
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    client = CarlaClient(args.host, args.port, args.timeout)
    metadata = client.record(args.output, args.frames, args.vehicle_id, args.episode_id)
    print(f"Recorded {metadata['frames_recorded']} frames to {args.output.resolve()}")


if __name__ == "__main__":
    main()
