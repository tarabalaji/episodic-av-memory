from dataclasses import replace
import pytest
from src.memory.memory_schema import RawDrivingEvent


@pytest.fixture
def event_factory():
    base = RawDrivingEvent("e0", "episode0", 0.0, "normal_driving", "Observed road.",
                           8.0, 25.0, 5.0, "clear", "urban", "maintain", "successful")
    def make(index=0, **changes):
        return replace(base, event_id=f"e{index}", timestamp=float(index), **changes)
    return make
