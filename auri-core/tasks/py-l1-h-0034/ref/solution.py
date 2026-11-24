# AURI-CANARY-da3844a0-e5ff-5ad1-a8d9-221569c068c3
# Reference solution: only for validating the task.
def hamming(a, b):
    if len(a) != len(b):
        raise ValueError('eltérő hossz')
    return sum(x != y for x, y in zip(a, b, strict=True))
