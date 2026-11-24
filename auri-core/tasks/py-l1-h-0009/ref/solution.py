# AURI-CANARY-406989fe-c7d3-5cd8-9b79-097f9d89619c
# Reference solution: only for validating the task.
def matrix_szorzas(a, b):
    if not a or not b or len(a[0]) != len(b):
        raise ValueError('méret')
    return [[sum(x * y for x, y in zip(r, c, strict=True)) for c in zip(*b, strict=True)] for r in a]
