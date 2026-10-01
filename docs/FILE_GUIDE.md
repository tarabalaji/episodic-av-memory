# File-by-file guide

| File | Responsibility |
| --- | --- |
| `configs/default.yaml` | Offline defaults, paths, capacity, retrieval k, compression window, and planner selection. |
| `src/memory/memory_schema.py` | Validated event/memory records, episode-aware IDs, provenance, occurrence/access counts. |
| `src/memory/memory_builder.py` | Event-to-memory conversion and initial importance/protection. |
| `src/memory/memory_manager.py` | Capacity enforcement, duplicate rejection, transactional rollback, strategy progress guard. |
| `src/memory/errors.py` | Explicit protected-capacity exception. |
| `src/memory/memory_database.py` | Atomic SQLite snapshot replacement and restoration. |
| `src/memory/strategies/fifo.py` | Oldest-insertion eviction baseline. |
| `src/memory/strategies/importance.py` | Transparent weighted importance and eviction. |
| `src/memory/strategies/compression.py` | Conservative within-episode repeated-event aggregation. |
| `src/memory/strategies/core_safety.py` | Heuristic protection and unprotected-record eviction. |
| `src/retrieval/embedder.py` | Deterministic normalized lexical vectors; no model downloads. |
| `src/retrieval/retriever.py` | Exact cosine ranking, top-k selection, actual access counting. |
| `src/planner/llm_planner.py` | Offline advisory rules and optional validated OpenAI output. |
| `src/pipeline.py` | Causal replay, storage, trace production, explicit no-memory/unlimited conditions. |
| `src/evaluation/metrics.py` | Coverage, retention, retrieval, capacity, and storage diagnostics. |
| `src/evaluation/experiments.py` | Group-aware comparisons, paired bootstrap, provenance, CSV/JSON/HTML. |
| `src/simulation/data_logger.py` | Strict JSON/JSONL ingestion and thread-safe append logging. |
| `src/simulation/sensors.py` | CARLA sensor ownership, callbacks, frame buffers, TTC estimate, cleanup. |
| `src/simulation/carla_client.py` | Optional local/remote passive recorder and run metadata. |
| `src/utils/helpers.py` | Validated configuration and atomic JSON output. |
| `scripts/run_pipeline.py` | Demo/replay command. |
| `scripts/evaluate.py` | Six-condition evaluation command. |
| `scripts/generate_benchmark.py` | Reproducible synthetic stress dataset and manifest. |
| `scripts/start_carla.py` | Guided prompts, read-only connection check, friendly errors, and report opening. |
| `src/simulation/connection.py` | Host validation, version matching, and read-only vehicle/map inspection. |
| `src/simulation/demo_vehicle.py` | Optional owned Traffic Manager vehicle with bounded spawn attempts and cleanup. |
| `src/simulation/session.py` | Connect-to-record-to-analysis workflow, unique outputs, progress, and offline check. |
| `tests/test_carla_launcher.py` | Fake-server launcher integration, ownership, failure cleanup, input and version checks. |
| `scripts/collect_carla.py` | CARLA recorder command. |
| `tests/test_memory_manager.py` | Original strategy tests, with corrected compression/access-count expectation. |
| `tests/test_memory_regressions.py` | Rollback, overflow, nonprogressing strategies, clocks, distinct-outcome compression. |
| `tests/test_pipeline.py` | All strategies, causal ordering, persistence, saturation, label leakage, coverage. |
| `tests/test_retrieval.py` | Ranking, accesses, empty/unmatched queries, invalid k. |
| `tests/test_data_and_storage.py` | Invalid data, unknown sensor values, JSONL and SQLite roundtrips, atomic failures. |
| `tests/test_planner.py` | Rule-based memory use and mocked OpenAI validation/input isolation. |
| `tests/test_experiments.py` | Reproducible intervals/generation, baseline comparisons, exports. |
| `tests/test_carla.py` | Fake-server recording, failure cleanup, stale/future sensors, missing dependency. |
| `src/evaluation/annotations.py` | Exhaustive graded query validation, causal references, separate evaluator-only labels. |
| `src/evaluation/ranking.py` | Precision, source recall, MRR, and nDCG with explicit compression semantics. |
| `src/evaluation/protocol.py` | Scenario grouping, split selection, and cross-split leakage checks. |
| `src/evaluation/output.py` | Fresh result directories, run status, and exclusive reservation. |
| `tests/test_research_protocol.py` | Hand-calculated metrics, label isolation, grouping, split leakage, reproducibility, and output preservation. |
| `data/examples/` | Clearly labeled illustrative query judgments and protocol. |
| `requirements-lock.txt` | Exact dependency versions from the tested local environment. |
| `.github/workflows/tests.yml` | Offline tests across Python versions; no secrets or simulator required. |

Package `__init__.py` files intentionally contain no behavior. Generated results,
virtual environments, secrets, and Python caches are excluded from version control.
