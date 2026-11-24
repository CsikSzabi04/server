# AURI-CANARY-b2ae44a1-1b79-54d0-9c58-a30741c61832
# Reference solution: only for validating the task.
from collections import Counter


def modusz(xs):
    if not xs:
        return None
    c = Counter(xs)
    return min(c, key=lambda x: (-c[x], x))
