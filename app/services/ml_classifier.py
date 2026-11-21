"""Tiny multinomial Naive Bayes over merchant tokens, trained on the user's own labelled history.

Pure Python on purpose: the data is a few thousand short strings, so scikit-learn would add a heavy
dependency for no benefit.
"""
import math
from collections import Counter, defaultdict

from app.utils.text import tokens

MIN_TRAINING = 20
MIN_CONFIDENCE = 0.8


class MerchantClassifier:
    def __init__(self) -> None:
        self._class_counts: Counter[int] = Counter()
        self._token_counts: dict[int, Counter[str]] = defaultdict(Counter)
        self._vocab: set[str] = set()

    @property
    def trained(self) -> bool:
        return sum(self._class_counts.values()) >= MIN_TRAINING and len(self._class_counts) >= 2

    def fit(self, samples: list[tuple[str, int]]) -> "MerchantClassifier":
        for text, label in samples:
            toks = tokens(text)
            if not toks:
                continue
            self._class_counts[label] += 1
            self._token_counts[label].update(toks)
            self._vocab.update(toks)
        return self

    def predict(self, text: str) -> tuple[int, float] | None:
        toks = [t for t in tokens(text) if t in self._vocab]
        if not self.trained or not toks:
            return None
        total = sum(self._class_counts.values())
        v = len(self._vocab)
        scores: dict[int, float] = {}
        for label, count in self._class_counts.items():
            denom = sum(self._token_counts[label].values()) + v
            scores[label] = math.log(count / total) + sum(
                math.log((self._token_counts[label][t] + 1) / denom) for t in toks)
        best = max(scores.values())
        exp = {k: math.exp(s - best) for k, s in scores.items()}
        norm = sum(exp.values())
        label, prob = max(((k, e / norm) for k, e in exp.items()), key=lambda kv: kv[1])
        return (label, prob) if prob >= MIN_CONFIDENCE else None
