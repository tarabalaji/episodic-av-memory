"""SQLite persistence for a retained-memory snapshot, including access counts."""
import json
from pathlib import Path
import sqlite3
from src.memory.memory_schema import DrivingMemory


class MemoryDatabase:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS memories (position INTEGER, memory_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )

    def save(self, memories):
        # Serialize before the transaction so invalid data cannot erase a snapshot.
        rows = [(i, m.memory_id, json.dumps(m.to_dict(), allow_nan=False))
                for i, m in enumerate(memories)]
        with self.connection:
            self.connection.execute("DELETE FROM memories")
            self.connection.executemany("INSERT INTO memories VALUES (?, ?, ?)", rows)

    def load(self):
        rows = self.connection.execute("SELECT payload FROM memories ORDER BY position")
        return [DrivingMemory.from_dict(json.loads(row[0])) for row in rows]

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
