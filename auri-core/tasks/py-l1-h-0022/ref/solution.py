# AURI-CANARY-7c79804c-b658-54e3-b1ae-af97f1a54553
# Reference solution: only for validating the task.
import math


def kombinacio(n, k):
    if n < 0:
        raise ValueError(n)
    return math.comb(n, k) if 0 <= k <= n else 0
