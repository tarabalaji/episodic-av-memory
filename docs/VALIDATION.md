# Validation performed

Validated on the existing local Python 3.14.6 environment on macOS.

- `python -m pytest -q`: **161 passed**.
- Every Python source, script, and test compiled successfully.
- `git diff --check`: passed.
- Original ten-event demo completed with a saved JSON report and SQLite snapshot.
- Demo launched successfully from outside the project directory.
- Six-condition comparison completed for the supplied two-episode dataset.
- Synthetic benchmark: 20 episodes × 80 events = 1,600 events; six conditions at
  capacities 5, 15, and 30, producing 360 independent episode-condition-budget runs.
- Bootstrap: 2,000 resamples, seed 42. Synthetic generator: seed 42.
- CARLA command help works without CARLA installed.
- Fake CARLA tests cover recording, sensor errors/overflow/staleness, partial
  startup and timeout cleanup, log roundtrip, and overwrite protection.
- Mocked OpenAI tests cover input isolation, valid output, and malformed output.

## Not validated here

No live CARLA server or live OpenAI API was called. No vehicle was controlled.
The new CI matrix for Python 3.11–3.13 has not yet run on GitHub. Cross-platform
installation and simulator-version compatibility need testing on target systems.
Unit tests are not a security audit, proof of correctness, or a scientific study.

The original compression access-count test was corrected: merging two records
with two and three accesses yields five actual accesses, not six. Occurrences are
counted separately. Original tracked bytecode was removed and caches ignored.

The source-code fingerprint in each comparison manifest covers Python files in
src/scripts/tests, YAML files in configs, and requirements files. Data fingerprints cover canonicalized
validated event records. Timing, timestamps, platform, and working-tree status
will naturally differ between runs; compare scientific metrics separately.


## Research evaluation upgrade

- Hand-calculated precision, source recall, MRR, and graded nDCG tests pass.
- Relevance-label changes cannot change retrieval, plans, or retained memories.
- Missing/self/future judgments are rejected.
- Entire datasets are validated before any planner calls.
- Repeated episodes are aggregated by declared group; cross-split groups fail.
- Single-group experiments produce no confidence interval.
- Repeated evaluation produces identical non-timing summary metrics.
- Failed experiments preserve failure status; existing outputs cannot be replaced.
- Unknown/duplicate/nonfinite experiment settings are rejected; duplicate JSON keys and nonstandard NaN/Infinity values are also rejected.
- The labeled-query example and full 1,600-event synthetic comparison completed
  under the upgraded evaluator. Example labels are illustrative, not human data.


## Guided CARLA launcher

- 161 tests pass, including the original research tests and launcher integration.
- A real `--offline --no-browser` launcher run produced a completed comparison.
- Missing CARLA on the current Mac yields setup guidance and a nonzero exit code.
- `--help` works with Python site packages disabled.
- Fake-server tests cover read-only inspection, mismatched versions, existing
  vehicle recording, demo spawning/autopilot, occupied spawn points, startup
  failures, timeouts, Ctrl+C, cleanup, unique outputs, and the full prompted flow.
- No real CARLA server was contacted and no live vehicle was created. Traffic
  Manager behavior and client/server networking still require live verification.
