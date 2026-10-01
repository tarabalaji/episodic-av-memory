# Experimental protocol and reporting limits

## Supported experiments

The experiment runner compares six conditions: no memory, unlimited prior-event
memory, FIFO, importance, compression, and core safety. All conditions see the
same ordered observations, use the same lexical retriever and rule-based planner,
and start with an empty store for each episode. No model is fitted to the test
episodes. An optional protocol selects a split and prevents groups crossing splits. A decision uses only earlier events; learning follows the decision.

The unlimited condition is a storage upper baseline, not access to future events.
No-memory and unlimited results are repeated at each nominal budget for convenient
paired tables, but their behavior does not depend on that budget. Do not treat
those repeated rows as independent trials.

Episode order is retained from the input. Events are never randomly shuffled.
The random seed controls synthetic generation, bootstrap resampling, and shuffled
condition execution order; it does not change the deterministic strategies. Timing remains machine-dependent.

## Retention algorithms

- FIFO removes the oldest insertion. It deliberately ignores protection flags as
  an unprotected baseline.
- Importance removes the lowest score among unprotected records. Its components
  are severity (0.30), urgency (0.25), observed outcome (0.20), actual retrieval
  frequency (0.10), and recency (0.15). In the replay pipeline, recency uses global
  event index to avoid comparing episode-local clocks. Direct standalone use
  without sequence indices uses timestamps. Report the relevant unit.
- Compression merges records only within the same episode and temporal window,
  with matching event type, weather, road type, action, and outcome. It keeps
  the maximum speed/importance, minimum known clearance/TTC, combined occurrence
  count, summed actual accesses, protection, and source IDs. The oldest record's
  description remains the representative text. The time window applies to the
  latest representative timestamp, so long bursts can merge transitively.
  Without a match, it removes the oldest unprotected representative.
- Core safety protects critical event types, adverse outcomes, emergency actions,
  very low TTC, and very short clearance. These are heuristic labels; a close
  parking maneuver can be marked critical. Validate thresholds for the domain.

When all available records are protected, insertion is rejected and counted.
An unsuccessful insertion restores the prior store and object fields. Core
safety therefore does not guarantee retaining every future critical event after
saturation. It never silently exceeds the configured record budget.

Compression keeps source identities to measure coverage. Those IDs and trace
files can grow without bound even though record count is bounded. This is not a
fixed-byte-memory algorithm. `retained_json_bytes` reports serialized UTF-8 JSON
size, not peak RAM or SQLite size. Full traces are evaluation artifacts outside
the retained-memory budget.

## Metrics

| Metric | Definition and caveat |
| --- | --- |
| Critical-event retention | Unique original heuristic-critical events represented at the end / all critical events seen. Null if there were none. |
| Event coverage | Unique original events represented by retained records / all events seen. Compression can represent multiple source events. |
| Same-type recall at k | For each event with matching-type history, fraction of all earlier same-type events represented among the top-k retrieved records. Includes evicted history in the denominator. Null without eligible queries. |
| Retrieval hit rate | Fraction of events returning at least one positive lexical similarity. Shared weather/road tokens can cause hits; this is not precision. |
| Mean retrieval milliseconds | Token-vector construction plus exact ranking per query, excluding planning and storage. One timed run; small values are noisy. |
| Capacity rejections | New records rejected because no protected record can be removed. Ordinary successful eviction is not a rejection. |
| Retained JSON bytes | Serialized record payload size, including provenance. |

Reported summaries first average episodes within each declared scenario group,
then weight the group means equally. Without a protocol, each episode is its own group.
The first query in every episode is a cold start. Undefined metrics remain null;
they are omitted from that metric's interval, with the contributing episode count
reported separately from the independent group count. A compressed representative can cover several relevant originals;
recall is source-event coverage, not ordinary document-level recall.

Confidence intervals use 2,000 group bootstrap samples by default and empirical
2.5/97.5 percentiles. Paired differences subtract FIFO within each episode, average within groups, then
resample group means. A single group gets no interval. Tiny episode counts produce
unstable intervals; repeated frames or correlated routes are not independent
replicates. For correlated runs, supply a protocol grouping runs at the independent scenario
or route level; the evaluator performs this aggregation and resampling. Intervals are exploratory, with no multiplicity correction or
formal significance claim. Do not rerun until a favorable seed appears.

## Requirements for a defensible paper

1. State hypotheses and select primary metrics before selecting budgets or
   thresholds; tune on separate development scenarios.
2. Collect enough independent routes/scenarios and independent traffic/weather
   seeds for uncertainty estimates, documenting exclusions and failed runs.
3. Validate that observations and event labels exist at decision time. Separate
   retrospective event annotation from prospective planner input.
4. Add independently labeled retrieval queries and assess precision, recall, and
   rank quality beyond the current event-type proxy. The query contains event
   type, so this proxy is particularly favorable to lexical matching.
5. Compare equivalent byte budgets if claiming storage efficiency, including
   index/provenance overhead. Include semantic retrieval and heuristic ablations
   if the paper claims advantages beyond the implemented lexical baseline.
6. Run controlled closed-loop CARLA experiments for any claim about collision
   rate, route completion, comfort, interventions, or causal safety improvement.
   Replay of recorded outcomes cannot show what an alternative planner would do.
7. Record simulator, maps, vehicle/controller versions, traffic seeds, timing,
   model/prompt versions, costs, raw results, and code/data fingerprints.
8. Report failures, protected-memory saturation, uncertainty, limitations, and
   negative results. Human review and real experiments remain necessary.

The bundled ten events and synthetic generator validate software behavior only.
They cannot establish scientific novelty, generalization, or driving safety.


## Labeled-query extension

`docs/RESEARCH_EVALUATION.md` specifies the optional graded relevance protocol and
ranking metrics. Annotated metrics supplement the type-matching proxy; the
bundled example labels are synthetic demonstrations. No human-labeled evidence
has been supplied or fabricated. Fresh experiment directories, failed-run status,
full-input/selected-input/annotation fingerprints, exact local dependency versions,
and strict configuration validation support reproducibility and auditing.
