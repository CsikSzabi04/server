# AURI-CANARY-6ce2a96c-718b-52ed-9383-7b71dc575559
# Reference solution: only for validating the task.
def min_ermek(osszeg, cimletek):
    if osszeg < 0:
        raise ValueError(osszeg)
    inf = osszeg + 1
    best = [inf] * (osszeg + 1)
    best[0] = 0
    for v in range(1, osszeg + 1):
        for c in cimletek:
            if c <= v and best[v - c] + 1 < best[v]:
                best[v] = best[v - c] + 1
    return best[osszeg] if best[osszeg] < inf else -1
