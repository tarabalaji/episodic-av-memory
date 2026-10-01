import pytest
from src.memory.memory_builder import MemoryBuilder
from src.retrieval.retriever import MemoryRetriever


def test_retrieval_ranks_content_and_counts_only_selected_accesses(event_factory):
    builder = MemoryBuilder()
    pedestrian = builder.build(event_factory(0, event_type="pedestrian_crossing", description="pedestrian crosswalk"))
    rain = builder.build(event_factory(1, event_type="heavy_rain", description="rain visibility", weather="rain"))
    results = MemoryRetriever().retrieve("pedestrian crosswalk", [rain, pedestrian], top_k=1)
    assert results[0].memory is pedestrian
    assert pedestrian.access_count == 1 and rain.access_count == 0
    assert 0 < results[0].score <= 1.00000001


def test_no_overlap_and_empty_queries_do_not_retrieve(event_factory):
    memory = MemoryBuilder().build(event_factory())
    retriever = MemoryRetriever()
    assert retriever.retrieve("xylophone", [memory]) == []
    assert retriever.retrieve(" ", [memory]) == []
    assert retriever.retrieve("urban", []) == []
    assert memory.access_count == 0


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_invalid_k(top_k):
    with pytest.raises(ValueError):
        MemoryRetriever().retrieve("road", [], top_k)
