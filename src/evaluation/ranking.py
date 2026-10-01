"""Graded ranking metrics, explicitly accounting for compressed representatives."""
from math import log2

RANKING_METRICS = ("annotated_precision_at_k", "annotated_source_recall_at_k",
                   "annotated_mrr_at_k", "annotated_ndcg_at_k")


def ranked_metrics(retrieved, relevance, k):
    """P@k and DCG count representatives; recall counts original source events.

    A representative receives the maximum grade among its source events. This
    measures provenance coverage, NOT semantic faithfulness of a compressed text.
    Ideal DCG is computed over all judged original events, including evicted ones.
    """
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer.")
    if any(type(grade) is not int or not 0 <= grade <= 3 for grade in relevance.values()):
        raise ValueError("Relevance grades must be integers between 0 and 3.")
    represented, grades = set(), []
    for result in retrieved[:k]:
        sources = set(result.memory.source_memory_ids)
        if len(sources) != len(result.memory.source_memory_ids) or represented & sources:
            raise ValueError("Retrieved representatives must have disjoint source identities.")
        if not sources <= relevance.keys():
            raise ValueError("Retrieved unjudged event; exhaustive judgments are required.")
        represented.update(sources)
        grades.append(max((relevance[identity] for identity in sources), default=0))
    positives = {identity for identity, grade in relevance.items() if grade > 0}
    dcg = sum((2 ** grade - 1) / log2(rank + 2) for rank, grade in enumerate(grades))
    ideal = sum((2 ** grade - 1) / log2(rank + 2)
                for rank, grade in enumerate(sorted(relevance.values(), reverse=True)[:k]))
    return {
        "annotated_precision_at_k": sum(grade > 0 for grade in grades) / k,
        "annotated_source_recall_at_k": len(positives & represented) / len(positives) if positives else None,
        "annotated_mrr_at_k": next((1 / (rank + 1) for rank, grade in enumerate(grades) if grade > 0), 0.0)
                              if positives else None,
        "annotated_ndcg_at_k": dcg / ideal if ideal else None,
    }
