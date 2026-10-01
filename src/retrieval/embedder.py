"""Offline lexical vectors; no model downloads, training, or API calls."""
from collections import Counter
import math
import re


class Embedder:
    def encode(self, texts: list[str]) -> list[dict[str, float]]:
        vectors = []
        for text in texts:
            counts = Counter(re.findall(r"[a-z0-9]+", text.lower()))
            norm = math.sqrt(sum(count * count for count in counts.values()))
            vectors.append({token: count / norm for token, count in counts.items()} if norm else {})
        return vectors

    @staticmethod
    def similarity(first, second):
        return sum(weight * second.get(token, 0.0) for token, weight in first.items())
