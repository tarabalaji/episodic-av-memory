"""Run with python -m scripts.run_pipeline (or python scripts/run_pipeline.py)."""
import argparse
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline import run_pipeline
from src.planner.llm_planner import LLMPlanner
from src.simulation.data_logger import load_events
from src.utils.helpers import load_config, STRATEGIES


def main(argv=None):
    parser = argparse.ArgumentParser(description="Replay recorded driving events with episodic memory.")
    parser.add_argument("--config")
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strategy", choices=STRATEGIES + ("no_memory", "unlimited"))
    parser.add_argument("--capacity", type=int)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    report = run_pipeline(load_events(args.events or config["events_path"]),
        strategy=args.strategy or config["strategy"],
        capacity=args.capacity if args.capacity is not None else config["capacity"],
        top_k=config["top_k"], similarity_window=config.get("similarity_window", 10.0),
        planner=LLMPlanner(config["planner"], config.get("model")),
        output_dir=args.output or config["output_dir"])
    print(f"Completed {report['metrics']['events_processed']} events using {report['strategy']}.")
    print(f"Results: {Path(args.output or config['output_dir']).resolve()}")
    return report


if __name__ == "__main__":
    main()
