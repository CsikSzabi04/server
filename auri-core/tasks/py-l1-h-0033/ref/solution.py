# AURI-CANARY-e6ad6851-b7c7-5783-aeae-03d6edfacdf1
# Reference solution: only for validating the task.
from collections import Counter


def elso_egyedi(s):
    c = Counter(s)
    return next((ch for ch in s if c[ch] == 1), None)
