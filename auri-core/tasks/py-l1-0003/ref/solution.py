# Reference solution: only for validating the task (green on visible + hidden tests).
from collections import Counter


def top_words(text: str, k: int) -> list[tuple[str, int]]:
    if k < 0:
        raise ValueError("k nem lehet negatív")
    words: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalpha():
            current.append(ch)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    counts = Counter(w.lower() for w in words)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
