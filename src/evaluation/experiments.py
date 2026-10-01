"""Independent-episode evaluation with paired episode bootstrap intervals."""
from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import html
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
from statistics import mean
import subprocess
from src.pipeline import run_pipeline
from src.evaluation.annotations import validate_annotations
from src.evaluation.protocol import validate_protocol
from src.evaluation.ranking import RANKING_METRICS
from src.evaluation.output import experiment_directory
from src.simulation.data_logger import validate_event_sequence
from src.utils.helpers import PROJECT_ROOT, STRATEGIES, write_json

METRICS = ("critical_event_retention", "event_coverage", "same_type_recall_at_k",
           "retrieval_hit_rate", "mean_retrieval_ms", "capacity_rejections", "retained_json_bytes")


def interval(values, seed=42, samples=2000):
    """Percentile 95% bootstrap over independent episode-level estimates."""
    if type(samples) is not int or samples < 100:
        raise ValueError("Use at least 100 bootstrap samples.")
    values = [float(v) for v in values if v is not None]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Bootstrap observations must be finite.")
    if not values:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    if len(values) < 2:
        return {"mean": mean(values), "ci_low": None, "ci_high": None, "n": len(values)}
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choices(values, k=len(values))) for _ in range(samples))
    return {"mean": mean(values), "ci_low": estimates[int(.025 * (samples - 1))],
            "ci_high": estimates[int(.975 * (samples - 1))], "n": len(values)}


def provenance(events, settings):
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT,
                                           stderr=subprocess.DEVNULL).decode().strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    source = hashlib.sha256()
    for base in ("src", "scripts", "configs", "tests"):
        for path in sorted((PROJECT_ROOT / base).rglob("*")):
            if path.suffix in (".py", ".yaml"):
                source.update(str(path.relative_to(PROJECT_ROOT)).encode())
                source.update(path.read_bytes())
    for name in ("requirements.txt", "requirements-optional.txt", "requirements-lock.txt"):
        source.update(name.encode())
        source.update((PROJECT_ROOT / name).read_bytes())
    versions = {}
    for package in ("PyYAML", "pytest", "openai"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {"created_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": versions, "git_commit": git("rev-parse", "HEAD"),
            "git_status": git("status", "--short"), "source_sha256": source.hexdigest(),
            "data_sha256": hashlib.sha256(json.dumps([e.to_dict() for e in events],
                 sort_keys=True, allow_nan=False).encode()).hexdigest(),
            "settings": settings, "protocol": "grouped_causal_replay_v2"}


def grouped_interval(rows, metric, groups, seed, samples):
    """Equal episode means within groups, then equal independent group weights."""
    grouped = defaultdict(list)
    for row in rows:
        if row[metric] is not None:
            grouped[groups[row["episode_id"]]].append(row[metric])
    result = interval([mean(values) for values in grouped.values()], seed, samples)
    result["n_episodes"] = sum(len(values) for values in grouped.values())
    return result


def evaluate(events, output_dir, capacities=(2, 5, 10), top_k=3, seed=42,
             bootstrap_samples=2000, similarity_window=10.0, data_kind="unspecified",
             annotations=None, protocol=None, split=None):
    if type(bootstrap_samples) is not int or bootstrap_samples < 100:
        raise ValueError("Use at least 100 bootstrap samples.")
    if type(seed) is not int:
        raise ValueError("seed must be an integer.")
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    if not math.isfinite(similarity_window) or similarity_window < 0:
        raise ValueError("similarity_window must be finite and nonnegative.")
    if data_kind not in ("unspecified", "synthetic", "recorded"):
        raise ValueError("Unknown data kind.")
    events = validate_event_sequence(events)
    if not events:
        raise ValueError("Evaluation requires at least one event.")
    capacities = list(capacities)
    if not capacities or any(type(c) is not int or c < 1 for c in capacities) or len(set(capacities)) != len(capacities):
        raise ValueError("Capacities must be distinct positive integers.")
    selected, groups = validate_protocol(events, protocol, split)
    if annotations is not None:
        validated = validate_annotations(events, annotations)
        if not any(key[0] in selected for key in validated):
            raise ValueError("No annotated queries belong to the selected split.")
    selected_events = [event for event in events if event.episode_id in selected]
    episodes = defaultdict(list)
    for event in selected_events:
        episodes[event.episode_id].append(event)
    annotation_by_episode = {}
    if annotations is not None:
        for episode_id in episodes:
            queries = [row for row in annotations["queries"] if row["episode_id"] == episode_id]
            annotation_by_episode[episode_id] = {**annotations, "queries": queries} if queries else None
    settings = {"capacities": capacities, "top_k": top_k, "seed": seed,
                "bootstrap_samples": bootstrap_samples, "similarity_window": similarity_window,
                "planner": "rule_based", "retrieval": "normalized_token_counts", "data_kind": data_kind,
                "split": split, "groups": groups, "protocol": protocol,
                "label_source": annotations["label_source"] if annotations else None,
                "summary_weighting": "equal groups of equal episode means",
                "bootstrap_unit": "group", "execution_order": "seeded shuffle"}
    manifest = provenance(events, settings)
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()
    manifest["selected_data_sha256"] = digest([event.to_dict() for event in selected_events])
    manifest["annotations_sha256"] = digest(annotations) if annotations is not None else None
    strategies = ("no_memory", "unlimited") + STRATEGIES
    jobs = [(budget, strategy, index, identity) for budget in capacities
            for strategy in strategies for index, identity in enumerate(episodes)]
    random.Random(seed).shuffle(jobs)
    records = []
    with experiment_directory(output_dir) as output:
        write_json(output / "manifest.json", manifest)
        write_json(output / "execution_order.json", jobs)
        for capacity, strategy, episode_index, episode_id in jobs:
            report = run_pipeline(episodes[episode_id], capacity=capacity, strategy=strategy, top_k=top_k,
                                  similarity_window=similarity_window,
                                  annotations=annotation_by_episode.get(episode_id))
            records.append({"episode_id": episode_id, "group_id": groups[episode_id],
                            "strategy": strategy, "budget": capacity, **report["metrics"]})
            write_json(output / "runs" / f"{strategy}_{capacity}_{episode_index:05}.json", report)
        records.sort(key=lambda row: (row["budget"], row["strategy"], row["episode_id"]))
        summaries, comparisons = [], []
        metrics = METRICS + (RANKING_METRICS if annotations is not None else ())
        for capacity in capacities:
            for strategy in strategies:
                chosen = [r for r in records if r["strategy"] == strategy and r["budget"] == capacity]
                baseline = {r["episode_id"]: r for r in records if r["strategy"] == "fifo" and r["budget"] == capacity}
                for metric in metrics:
                    summaries.append({"strategy": strategy, "budget": capacity, "metric": metric,
                        **grouped_interval(chosen, metric, groups, seed, bootstrap_samples)})
                    differences = [{"episode_id": r["episode_id"], metric: r[metric] - baseline[r["episode_id"]][metric]}
                                   for r in chosen if r[metric] is not None and baseline[r["episode_id"]][metric] is not None]
                    comparisons.append({"strategy": strategy, "baseline": "fifo", "budget": capacity,
                        "metric": metric, **grouped_interval(differences, metric, groups, seed, bootstrap_samples)})
        warnings = ["Offline retention/retrieval diagnostics do not measure collision reduction or closed-loop safety.",
                    "Event-type recall is a proxy, not independently annotated semantic relevance.",
                    "Budgets constrain record count, not bytes; compression provenance grows with merged events.",
                    "Groups are assumed independent; repeated routes/seeds require scientifically justified grouping.",
                    "Multiple exploratory comparisons are reported without multiplicity-adjusted significance claims.",
                    "Retrieval timing is measured once per query; hardware noise and warm-up are not controlled."]
        if data_kind == "synthetic":
            warnings.insert(0, "SYNTHETIC DATA: software experiments, not measured driving performance.")
        elif data_kind == "unspecified":
            warnings.insert(0, "Dataset origin is unspecified; verify provenance before reporting empirical findings.")
        if annotations is not None:
            warnings.append(f"Annotation source: {annotations['label_source']}. Provenance coverage does not validate compressed-text faithfulness.")
        if protocol is None:
            warnings.append("No split/group protocol supplied; each episode is treated as an independent group.")
        if len(set(groups.values())) < 10:
            warnings.append("Fewer than 10 independent groups: intervals are unstable; treat this as a smoke test.")
        result = {"manifest": manifest, "warnings": warnings, "summary": summaries,
                  "paired_differences_vs_fifo": comparisons, "episodes": records}
        write_json(output / "comparison.json", result)
        for name, rows in (("summary", summaries), ("paired_differences", comparisons), ("episodes", records)):
            with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        def number(value):
            return "N/A" if value is None else f"{value:.4f}"
        table = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in
            (row["strategy"], row["budget"], row["metric"], number(row["mean"]),
             number(row["ci_low"]), number(row["ci_high"]), row["n"], row["n_episodes"])) + "</tr>" for row in summaries)
        page = ("<!doctype html><meta charset='utf-8'><title>ASDRP memory experiments</title>"
                "<style>body{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 20px}"
                "table{border-collapse:collapse;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid #ddd}"
                "th{background:#e9f0f5;position:sticky;top:0}li{margin:8px 0}</style>"
                "<h1>ASDRP episodic memory experiments</h1><p>Causal replay with "
                "equal-group means and 95% group bootstrap intervals.</p><ul>" +
                "".join(f"<li>{html.escape(w)}</li>" for w in warnings) +
                "</ul><table><thead><tr><th>Strategy</th><th>Budget</th><th>Metric</th><th>Mean</th>"
                "<th>CI low</th><th>CI high</th><th>Groups</th><th>Episodes</th></tr></thead><tbody>" + table + "</tbody></table>")
        (output / "comparison.html").write_text(page, encoding="utf-8")
    return result
