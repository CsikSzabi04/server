# AURI-CANARY-484c85b0-ba99-5cf0-95b4-abbfde8b3f07
# Reference solution: only for validating the task.
from collections import Counter


def anagramma(a, b):
    def k(s):
        return Counter(c for c in s.casefold() if not c.isspace())
    return k(a) == k(b)
