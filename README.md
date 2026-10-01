# ASDRP episodic memory for autonomous-driving research

A runnable research prototype for comparing FIFO, importance-based retention,
compression, and protected core-safety memories. Includes causal offline replay,
local retrieval, an advisory planner, SQLite snapshots, group-aware
experiments, and an optional passive CARLA recorder.

**Status:** offline pipeline and mocked integrations tested. Live CARLA and live
OpenAI requests have not been validated here. This is a research codebase, not a
validated driving controller. Generated synthetic results are software checks,
not evidence of collision reduction or publication-ready empirical findings.

## Quick start

Use Python 3.11 or newer for offline work. From this project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pytest -q
python -m scripts.run_pipeline
python -m scripts.evaluate
```

Your existing `venv` also works: use `venv/bin/python` instead of `python`.
The demo needs no API key, CARLA installation, pretrained model, or network access
after its two dependencies are installed.

The pipeline writes `data/processed/demo/report.json` and `memories.sqlite3`.
Evaluation writes `data/results/comparison/comparison.html`, CSV tables, a JSON
comparison, per-episode traces, and a provenance manifest. Open the HTML file in
a browser to inspect results. Each evaluation requires a fresh, empty output directory and refuses to overwrite
existing results. `run_status.json` records running, failed, or complete status.
Use a new `--output` path for every run; the single-run demo still replaces its own snapshot.

## Run a larger, explicitly synthetic experiment

```sh
python -m scripts.generate_benchmark --episodes 20 --events-per-episode 80 --seed 42
python -m scripts.evaluate --events data/processed/synthetic_events.json --data-kind synthetic --capacities 5 15 30 --output data/results/synthetic_comparison
```

Synthetic episodes include repeated event types and hazardous observations to
exercise eviction, compression, retrieval, and saturation. The generator saves
its own manifest. These episodes are not simulated driving trajectories.

## Configuration and overrides

Edit `configs/default.yaml`, or pass `--config path/to/config.yaml`. Paths inside
a configuration are relative to the project root; explicit command-line paths
are relative to your current directory.

```sh
python -m scripts.run_pipeline --strategy compression --capacity 3 --output data/processed/compression
python -m scripts.run_pipeline --events path/to/events.jsonl --strategy core_safety
python -m scripts.evaluate --events path/to/events.json --capacities 5 20 50 --seed 42 --bootstrap-samples 2000
```

The single-run pipeline preserves recorded file order and can retain memory
across episodes. The comparison runner deliberately **resets memory per episode**
and optionally groups related episodes for confidence intervals. Without a group
protocol it assumes episodes are independent. Do not
interpret these two protocols as the same experiment.

## Event format

See `data/raw/sample_events.json`. Input is a JSON array or a `.jsonl` file of event
objects. Required fields are `event_id`, `episode_id`, `timestamp`, `event_type`,
`description`, `speed`, `distance_to_obstacle`, `time_to_collision`, `weather`,
`road_type`, `action`, and `outcome`.

Units are seconds, metres, and metres/second. IDs must be nonempty strings;
episode/event ID pairs must be unique; timestamps must not decrease within an
episode. Unknown distance and TTC must be JSON `null`, not negative numbers,
NaN, infinity, or an invented zero. Extra/missing fields are rejected.

For each event, retrieval and planning happen **before** its outcome is stored.
The current action, outcome, and free-text description are excluded from the
query and planner input. Retrospective descriptions often disclose outcomes.
Current `event_type`, weather, road type, and numerical observations must still
be available at decision time for any prospective claims.

## Guided CARLA launcher

Run `python -m scripts.start_carla` on a computer with the matching CARLA client.
Enter the server IP/hostname, port, recording length, and a vehicle selection.
Recording, cleanup, analysis, and report creation then run automatically. Type
`demo` at the vehicle prompt to create an autopilot vehicle in an asynchronous
world. It is driven by CARLA Traffic Manager; the memory planner stays advisory.

Try the flow locally without CARLA using `python -m scripts.start_carla --offline`.
For a read-only connection check use `--host YOUR_SERVER --port 2000 --check --non-interactive`.
Read `docs/CARLA_LAUNCHER.md` for the one-time client setup, Mac compatibility,
remote use, demo ownership, synchronous-clock behavior, and troubleshooting.

## CARLA, including a remote server

You can develop and test this project without CARLA. For actual recording, use a
machine with a CARLA server and the matching Python client. CARLA's supported
Python versions may differ from the offline environment; use a compatible
separate environment if needed.

Start a scenario with an existing vehicle and a running simulation clock. Then:

```sh
python -m scripts.collect_carla --host SERVER_ADDRESS --port 2000 --vehicle-id 123 --frames 1000 --output data/raw/carla_run_001.jsonl
python -m scripts.run_pipeline --events data/raw/carla_run_001.jsonl
python -m scripts.evaluate --events data/raw/carla_run_001.jsonl --capacities 20 50 100 --output data/results/carla_run_001
```

Omit `--vehicle-id` only when exactly one existing vehicle has role `hero` or
`ego`. The recorder attaches obstacle and collision sensors and destroys only
those sensors on exit. It does not spawn or drive a vehicle, change world
settings, tick a synchronous world, configure Traffic Manager, or reset the
server. A synchronous world needs another client advancing its clock.

The recorder refuses to overwrite an existing event log, writes completion and
server metadata, and reports callback failures or queue overflow. TTC is a
constant-velocity line-of-sight estimate. Asynchronous sensor callbacks can lag;
non-collision outcomes remain `unlabeled`. Collision callback counts measure
contacts, not independent crashes. Sensor readings have a 0.5-second maximum
age. This passive recorder is a data-acquisition adapter, not a controlled
closed-loop evaluation harness.

## Optional OpenAI planner

```sh
python -m pip install -r requirements-optional.txt
```

Set `OPENAI_API_KEY` in your environment, then set `planner: openai` and an explicit
`model` supporting Responses API structured outputs in your configuration. This mode sends observations and retrieved memories
to the API and incurs normal API usage. No `.env` file is automatically loaded.
API errors propagate; malformed actions are rejected; no silent rule-based
fallback is counted as LLM output. Plans are advisory and never applied to CARLA.
The comparison runner intentionally uses the deterministic rule-based planner;
live LLM experiments need a separate controlled model/prompt protocol.

Implementation references: [official OpenAI SDK documentation](https://developers.openai.com/api/docs/libraries),
[CARLA Python API](https://carla.readthedocs.io/en/0.9.16/python_api/), and
[CARLA sensors](https://carla.readthedocs.io/en/0.9.16/ref_sensors/).

## Research interpretation

Read `docs/METHODOLOGY.md` before reporting results. Budgets constrain the number
of records, not total bytes. Provenance retained by compression can grow, so
serialized storage size is reported separately. Retrieval uses normalized token
counts (a transparent lexical baseline), not pretrained semantic embeddings.
Importance weights, safety thresholds, and compression criteria are explicit
heuristics, not learned or empirically validated optimal settings.

See `docs/FILE_GUIDE.md` for every source file and `docs/VALIDATION.md` for the
checks performed and remaining validation work.

## Annotated retrieval and held-out evaluation

Run the bundled **illustrative** relevance judgments and split protocol:

```sh
python -m scripts.evaluate --annotations data/examples/sample_annotations.json --protocol data/examples/sample_protocol.json --split test --output data/results/annotated_example
```

The example labels are declared `synthetic_demo`; they are not an independently
collected human benchmark. Supply your own prospective query text and relevance
judgments for real experiments. Each annotated query must grade every earlier
event in its episode from 0 (irrelevant) to 3 (highly relevant). Missing judgments,
future references, and self-references are rejected. Query text reaches the
retriever; relevance labels are used only by the evaluator.

The report adds precision@k, source-event recall@k, MRR@k, and nDCG@k. Grades on a
compressed record use its source provenance and cannot establish whether the
summary faithfully preserved every detail. See `docs/RESEARCH_EVALUATION.md` for
exact definitions and file schemas.

A protocol assigns every episode to a scenario group and a train/validation/test
split. Related episodes must share a group; a group cannot cross splits. Summaries
weight groups equally after averaging episodes within each group, and bootstrap
whole group means. Both contributing group and episode counts are reported.
This is split validation and evaluation infrastructure, not a training algorithm.

The `requirements-lock.txt` file captures exact versions from the tested local
environment. `requirements.txt` retains broader supported dependency ranges.
CI is configured for offline tests and the annotated evaluation. A fresh network
installation and the GitHub CI matrix have not been executed in this environment.
