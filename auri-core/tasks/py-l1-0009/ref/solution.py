# AURI-CANARY-133e53f7-598a-5318-b3cb-721ca4c3ef3a
# Reference solution: only for validating the task.
from itertools import groupby


def rle_kodol(s):
    return ''.join(f'{len(list(g))}{c}' for c, g in groupby(s))
