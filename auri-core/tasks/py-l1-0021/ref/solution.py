# AURI-CANARY-f0bd89d7-2749-5f0c-adad-a07a7ea32ff4
# Reference solution: only for validating the task.
def forgat(xs, k):
    if not xs:
        return []
    k %= len(xs)
    return xs[-k:] + xs[:-k] if k else list(xs)
