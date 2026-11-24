# AURI-CANARY-b125952b-42a0-51a4-b185-0020b7c2b34e
# Reference solution: only for validating the task.
def ket_osszeg(xs, cel):
    seen = {}
    for j, x in enumerate(xs):
        if cel - x in seen:
            return [seen[cel - x], j]
        seen.setdefault(x, j)
    return None
