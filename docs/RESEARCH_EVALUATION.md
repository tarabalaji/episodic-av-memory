# Graded retrieval evaluation and independent scenario groups

## Annotation schema

```json
{
  "schema_version": 1,
  "label_source": "human",
  "queries": [
    {
      "episode_id": "episode_001",
      "event_id": "003",
      "query": "What earlier experience helps with an approaching intersection?",
      "relevance": {"001": 0, "002": 2}
    }
  ]
}
```

This example assumes event 003 has exactly events 001 and 002 before it in the
same episode. Grades must cover *all* earlier events, including irrelevant ones.
Zero is irrelevant; 1, 2, and 3 are increasing relevance. Grades are integers,
not booleans. Duplicate query targets, unknown events, missing judgments, and
references to the current/future event are rejected before the experiment starts.

`human` is a declared provenance label, not a certification of annotation quality.
Use independent assessors, write an annotation rubric, record disagreements and
adjudication, and keep annotation/model-development and final-test work separate.
Query text must be available at decision time and must not reveal later outcomes.
The software cannot detect semantic leakage inside human-written text.

For demonstrations use `label_source: synthetic_demo`. The supplied sample labels
are illustrative; they must not be reported as an independent human benchmark.
Unannotated events still participate in replay, learning, and type-proxy metrics.
Annotated queries retrieve only from earlier memories in their own episode.
The experiment runner resets memory between episodes. Labels are never sent to
the retriever or planner and never used to choose which memories to retain.

## Metric definitions

Binary relevance means grade greater than zero. For the top k returned memory
representatives:

- Precision@k is relevant representatives divided by k. Missing results occupy
  unretrieved slots, so returning one relevant result at k=3 gives precision 1/3.
- Source recall@k is the fraction of all positive original source events covered
  by retrieved representatives, including evicted events in the denominator.
- MRR@k is the reciprocal of the first positive representative's rank, or zero
  when a relevant source exists but none is returned within k.
- DCG@k uses `(2**grade - 1) / log2(rank + 1)` with one-based ranks. nDCG divides
  by the ideal DCG obtained by sorting all earlier original event grades.

Each compressed representative receives the maximum grade among its source
identities. Ranking metrics count the representative once; source recall counts
all original identities it covers. Overlapping provenance between returned
representatives is rejected to prevent double counting. These conventions reduce
to ordinary graded ranking metrics for uncompressed records. They are a
provenance-based extension for compression, not proof of faithful text summaries.

With no relevant original events, recall, MRR, and nDCG are undefined (`null`),
while precision is zero. Query metrics are averaged within an episode over their
defined values; then episode means are averaged within a group; finally groups
have equal weight. This is not a pooled query-weighted average. Report query,
episode, and group counts alongside scores.

The conventional precision and nDCG definitions follow the
[Introduction to Information Retrieval textbook](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html).
The compressed-source scoring convention is specific to this implementation and
must be disclosed when comparing it to other research systems.

## Protocol schema

```json
{
  "schema_version": 1,
  "episodes": {
    "train_01": {"group_id": "route_A", "split": "train"},
    "test_01": {"group_id": "route_B", "split": "test"},
    "test_02": {"group_id": "route_B", "split": "test"}
  }
}
```

Every episode in the full input dataset must be assigned exactly once. Pass
`--protocol protocol.json --split test` (or `train`/`validation`). A scenario group
cannot cross splits. The evaluator uses only episodes in the selected split;
annotations and the protocol are validated against the full dataset first.
Choose groups that match the true independent sampling unit. The two test
episodes above contribute one group, so no confidence interval is reported.

The code computes equal-weighted group means and a paired group bootstrap against
FIFO. `n` in summary tables is the number of contributing groups; `n_episodes`
counts contributing episodes. Undefined metrics are omitted on a per-metric
basis. No p-values or multiple-testing-adjusted claims are produced. A declared
grouping cannot establish independence if the experimental design violates it.

## Reproducibility and failure behavior

Each experiment reserves a new directory and writes `run_status.json`. Only a
`complete` run should be used for analysis. In-progress or failed runs retain
their partial artifacts for inspection and cannot silently be overwritten.
A lock prevents two processes from sharing a result directory.

The manifest records full and selected data hashes, an annotation hash, protocol,
selected split, group definitions, label source, seed, dependency versions, and a
source fingerprint covering Python source/tests, YAML configs, and requirements.
`execution_order.json` records the seeded order of condition runs. Ordering is
shuffled to reduce fixed ordering effects, but timing still lacks controlled
warm-up and repeated hardware measurements. Timing is not bitwise reproducible.
Non-timing metrics are deterministic for unchanged inputs, settings, and code.

Configuration rejects unknown or duplicate keys instead of silently ignoring
typographical mistakes. The full event sequence is validated before any planning.
The exact local dependency snapshot is in `requirements-lock.txt`; it is not a
container image, an independent replication, or proof of cross-platform behavior.
