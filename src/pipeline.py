"""Causal offline replay: retrieve, plan, then learn the observed outcome."""
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from src.memory.memory_builder import MemoryBuilder
from src.memory.memory_manager import MemoryManager
from src.memory.errors import MemoryCapacityError
from src.memory.memory_database import MemoryDatabase
from src.memory.strategies.fifo import FIFOStrategy
from src.memory.strategies.importance import ImportanceStrategy
from src.memory.strategies.compression import CompressionStrategy
from src.memory.strategies.core_safety import CoreSafetyStrategy
from src.retrieval.retriever import MemoryRetriever
from src.planner.llm_planner import LLMPlanner, observation
from src.evaluation.metrics import summarize
from src.utils.helpers import write_json
from src.evaluation.annotations import validate_annotations
from src.evaluation.ranking import ranked_metrics
from src.simulation.data_logger import validate_event_sequence


def make_strategy(name, similarity_window=10.0):
    constructors = {"fifo": FIFOStrategy, "importance": ImportanceStrategy,
                    "compression": lambda: CompressionStrategy(similarity_window),
                    "core_safety": CoreSafetyStrategy}
    if name not in constructors:
        raise ValueError(f"Unknown strategy: {name}")
    return constructors[name]()


def run_pipeline(events, *, strategy="importance", capacity=5, top_k=3,
                 similarity_window=10.0, planner=None, output_dir=None, annotations=None):
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    # None means no memory; unlimited is an oracle storage baseline, not future access.
    if strategy not in ("no_memory", "unlimited"):
        manager = MemoryManager(capacity, make_strategy(strategy, similarity_window))
    else:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer.")
        manager = None
    events = validate_event_sequence(events)
    queries = validate_annotations(events, annotations) if annotations is not None else {}
    builder, retriever = MemoryBuilder(), MemoryRetriever()
    planner = planner or LLMPlanner()
    original, retained, trace = [], [], []
    for sequence, event in enumerate(events):
        identity = (event.episode_id, event.event_id)
        available = manager.get_memories() if manager is not None else retained
        # Exclude description/action/outcome from current query to avoid retrospective label leakage.
        query = " ".join(str(value) for key, value in observation(event).items()
                         if key in ("event_type", "weather", "road_type"))
        judged_query = queries.get(identity)
        if judged_query is not None:
            query = judged_query.query
            # Annotated relevance is scoped to earlier events in this episode.
            # Cross-episode retention is still allowed in ordinary replay.
            available = [m for m in available if m.episode_id == event.episode_id]
        start = perf_counter()
        retrieved = retriever.retrieve(query, available, top_k)
        retrieval_ms = (perf_counter() - start) * 1000
        judgment = ranked_metrics(retrieved, judged_query.relevance, top_k) if judged_query is not None else None
        plan = planner.plan(event, retrieved)
        # Relevant history is all earlier events of the same type, including evicted events.
        relevant = {m.memory_id for m in original if m.event_type == event.event_type}
        found = {identity for result in retrieved for identity in result.memory.source_memory_ids}
        recall = len(relevant & found) / len(relevant) if relevant else None
        memory = builder.build(event)
        memory.sequence_index = sequence
        original.append(deepcopy(memory))
        rejected = False
        if manager is not None:
            try:
                manager.add_memory(memory)
            except MemoryCapacityError:
                # Explicit reject-new policy when every slot is protected; never exceed capacity.
                rejected = True
            retained = manager.get_memories()
        elif strategy == "unlimited":
            retained.append(memory)
        trace.append({"sequence": sequence, "episode_id": event.episode_id,
                      "event_id": event.event_id, "memory_id": memory.memory_id,
                      "retrieved": [r.to_dict() for r in retrieved],
                      "plan": plan.to_dict(), "retrieval_ms": retrieval_ms,
                      "same_type_recall": recall, "annotated_metrics": judgment, "query": query,
                      "capacity_rejected": rejected,
                      "retained_ids": [m.memory_id for m in retained]})
    effective_capacity = max(1, len(events)) if strategy == "unlimited" else capacity
    report = {"strategy": strategy, "metrics": summarize(original, retained, trace, effective_capacity),
              "trace": trace, "memories": [m.to_dict() for m in retained]}
    if output_dir is not None:
        output = Path(output_dir)
        write_json(output / "report.json", report)
        with MemoryDatabase(output / "memories.sqlite3") as database:
            database.save(retained)
    return report
