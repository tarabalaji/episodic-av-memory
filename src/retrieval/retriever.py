"""Retrieve only the memories supplied by the bounded memory manager."""
from dataclasses import dataclass
from src.memory.memory_schema import DrivingMemory
from src.retrieval.embedder import Embedder


def memory_text(memory):
    return " ".join((memory.event_type, memory.description, memory.weather,
                     memory.road_type, memory.action, memory.outcome))


@dataclass
class RetrievalResult:
    memory: DrivingMemory
    score: float

    def to_dict(self):
        return {"memory_id": self.memory.memory_id, "score": self.score}


class MemoryRetriever:
    def __init__(self, embedder=None):
        self.embedder = embedder or Embedder()

    def retrieve(self, query: str, memories: list[DrivingMemory], top_k: int = 3):
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        if not query.strip() or not memories:
            return []
        vectors = self.embedder.encode([query] + [memory_text(m) for m in memories])
        ranked = [RetrievalResult(m, self.embedder.similarity(vectors[0], vector))
                  for m, vector in zip(memories, vectors[1:])]
        ranked = [result for result in ranked if result.score > 0]
        # Stable input ordering is the tie breaker; timestamps reset each episode.
        ranked.sort(key=lambda result: result.score, reverse=True)
        selected = ranked[:top_k]
        for result in selected:
            result.memory.access_count += 1
        return selected
