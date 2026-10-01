"""Generate explicitly synthetic repeated scenarios for software experiments."""
import argparse
from pathlib import Path
import random
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.memory.memory_schema import RawDrivingEvent
from src.utils.helpers import write_json, PROJECT_ROOT


def generate_benchmark(episodes=20, events_per_episode=80, seed=42):
    if type(episodes) is not int or type(events_per_episode) is not int or min(episodes, events_per_episode) < 1:
        raise ValueError("Episode and event counts must be positive integers.")
    rng = random.Random(seed)
    templates = [
        ("normal_driving", "urban", "maintain", "successful", 30.0, 9.0),
        ("red_light_stop", "intersection", "brake", "successful", 12.0, 5.0),
        ("school_zone", "residential", "slow_down", "successful", 20.0, 7.0),
        ("pedestrian_crossing", "urban", "hard_brake", "collision_avoided", 2.0, .8),
        ("near_collision", "highway", "emergency_brake", "collision_avoided", 1.0, .4),
        ("lane_change", "highway", "change_lane_left", "successful", 15.0, 5.0),
    ]
    result = []
    for episode in range(episodes):
        weather = rng.choice(["clear", "rain", "fog"])
        current = templates[0]
        for index in range(events_per_episode):
            # Bursts of repeated events exercise compression; no adversarial tuning to a strategy.
            if rng.random() > .45:
                current = rng.choices(templates, weights=[5, 3, 2, 1, 1, 3])[0]
            kind, road, action, outcome, distance, ttc = current
            result.append(RawDrivingEvent(str(index), f"synthetic_{episode:04}", float(index),
                kind, f"Synthetic {kind.replace('_', ' ')} observation.", rng.uniform(2, 12),
                distance, ttc, weather, road, action, outcome))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--events-per-episode", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/synthetic_events.json")
    args = parser.parse_args(argv)
    events = generate_benchmark(args.episodes, args.events_per_episode, args.seed)
    write_json(args.output, [event.to_dict() for event in events])
    write_json(args.output.with_suffix(".manifest.json"), {"synthetic": True,
        "seed": args.seed, "episodes": args.episodes, "events_per_episode": args.events_per_episode,
        "purpose": "Software stress/ablation tests; not empirical driving-safety evidence."})
    print(f"Saved {len(events)} synthetic events to {args.output}")


if __name__ == "__main__":
    main()
