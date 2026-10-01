"""Compare strategies at identical budgets with episode-level uncertainty."""
import argparse
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.experiments import evaluate
from src.simulation.data_logger import load_events
from src.utils.helpers import load_config, PROJECT_ROOT, read_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/results/comparison")
    parser.add_argument("--capacities", type=int, nargs="+", default=[2, 5, 10])
    parser.add_argument("--data-kind", choices=["unspecified", "synthetic", "recorded"], default="unspecified")
    parser.add_argument("--annotations", type=Path, help="Exhaustive relevance judgments and independent queries.")
    parser.add_argument("--protocol", type=Path, help="Scenario-group and dataset-split assignments.")
    parser.add_argument("--split", choices=["train", "validation", "test"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    result = evaluate(load_events(args.events or config["events_path"]), args.output,
                      args.capacities, config["top_k"], args.seed, args.bootstrap_samples,
                      config.get("similarity_window", 10.0), args.data_kind,
                      read_json(args.annotations) if args.annotations else None,
                      read_json(args.protocol) if args.protocol else None, args.split)
    print(f"Saved six-strategy comparison to {args.output.resolve()}")
    print("Offline diagnostics only; see comparison.html for results and limitations.")
    return result


if __name__ == "__main__":
    main()
