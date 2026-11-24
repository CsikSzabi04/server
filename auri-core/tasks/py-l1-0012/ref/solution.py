# AURI-CANARY-d07ae44e-2417-5637-8b12-d5b7ec49bb59
# Reference solution: only for validating the task.
from bisect import bisect_left


def binaris_kereses(xs, x):
    i = bisect_left(xs, x)
    return i if i < len(xs) and xs[i] == x else -1
