"""Explicit, exhaustively judged, causal retrieval queries. No generated ground truth."""
from collections import defaultdict
from dataclasses import dataclass
from src.memory.memory_schema import DrivingMemory


@dataclass(frozen=True)
class RetrievalQuery:
    episode_id: str
    event_id: str
    query: str
    relevance: dict[str, int]


def validate_annotations(events, payload):
    """Map each query to grades on *all* earlier source events in its episode.

    Missing grades are rejected rather than treating unjudged documents as negatives.
    Labels never enter the retriever or planner.
    """
    if not isinstance(payload, dict) or (type(payload.get("schema_version")) is not int or payload["schema_version"] != 1):
        raise ValueError("Annotations require schema_version: 1.")
    if payload.get("label_source") not in ("human", "synthetic_demo"):
        raise ValueError("Declare annotation label_source as human or synthetic_demo.")
    rows = payload.get("queries")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Annotations must contain a nonempty queries list.")
    histories, history = {}, defaultdict(dict)
    identities = set()
    for event in events:
        key = (event.episode_id, event.event_id)
        if key in identities:
            raise ValueError("Duplicate event identity in annotated dataset.")
        identities.add(key)
        histories[key] = dict(history[event.episode_id])
        history[event.episode_id][event.event_id] = DrivingMemory.from_event(event).memory_id
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"episode_id", "event_id", "query", "relevance"}:
            raise ValueError("Query fields must be episode_id, event_id, query, and relevance.")
        if any(not isinstance(row[name], str) or not row[name].strip()
               for name in ("episode_id", "event_id", "query")):
            raise ValueError("Query IDs and text must be nonempty strings.")
        key = (row["episode_id"], row["event_id"])
        if key not in histories or key in result:
            raise ValueError(f"Unknown or duplicate query event: {key}.")
        grades = row["relevance"]
        if not isinstance(grades, dict) or set(grades) != set(histories[key]):
            raise ValueError(f"Query {key} must judge exactly all earlier events in its episode; self/future references are forbidden.")
        if any(type(grade) is not int or not 0 <= grade <= 3 for grade in grades.values()):
            raise ValueError("Relevance grades must be integers from 0 to 3.")
        result[key] = RetrievalQuery(*key, row["query"],
            {histories[key][identity]: grade for identity, grade in grades.items()})
    return result
