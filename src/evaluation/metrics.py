"""Offline diagnostic metrics, not closed-loop driving safety measurements."""
from statistics import mean
import json
from src.memory.strategies.core_safety import CoreSafetyStrategy
from src.evaluation.ranking import RANKING_METRICS


def summarize(original, retained, trace, capacity):
    safety = CoreSafetyStrategy()
    critical = {m.memory_id for m in original if safety.is_critical(m)}
    represented = {identity for m in retained for identity in m.source_memory_ids}
    annotated = [row["annotated_metrics"] for row in trace if row.get("annotated_metrics") is not None]
    annotation_metrics = {}
    for name in RANKING_METRICS:
        values = [row[name] for row in annotated if row[name] is not None]
        annotation_metrics[name] = mean(values) if values else None
    return {
        **annotation_metrics,
        "annotated_queries": len(annotated),
        "events_processed": len(original),
        "memories_retained": len(retained),
        "retained_json_bytes": len(json.dumps([m.to_dict() for m in retained], allow_nan=False).encode()),
        "capacity": capacity,
        "capacity_utilization": len(retained) / capacity,
        "represented_events": len(represented),
        "event_coverage": len(represented) / len(original) if original else None,
        "critical_events": len(critical),
        "critical_event_retention": len(critical & represented) / len(critical) if critical else None,
        "capacity_rejections": sum(row["capacity_rejected"] for row in trace),
        "mean_retrieval_ms": mean(row["retrieval_ms"] for row in trace) if trace else 0.0,
        "retrieval_hit_rate": mean(bool(row["retrieved"]) for row in trace) if trace else None,
        "same_type_recall_at_k": mean(row["same_type_recall"] for row in trace
                                     if row["same_type_recall"] is not None)
             if any(row["same_type_recall"] is not None for row in trace) else None,
    }
