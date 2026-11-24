# AURI-CANARY-bd78a898-6b0a-5917-979a-d2da55b741ba
# Reference solution: only for validating the task.
def leghosszabb_novekvo(xs):
    best = cur = 0
    for i, x in enumerate(xs):
        cur = cur + 1 if i and x > xs[i - 1] else 1
        best = max(best, cur)
    return best
