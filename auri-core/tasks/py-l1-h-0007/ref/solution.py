# AURI-CANARY-766afb16-1347-57a4-b8ef-9024be4f3a20
# Reference solution: only for validating the task.
def mozgo_atlag(xs, k):
    if k < 1:
        raise ValueError(k)
    return [round(sum(xs[i:i + k]) / k, 2) for i in range(len(xs) - k + 1)]
