# AURI-CANARY-b441ad6a-a775-5482-8e0f-43e87d017ee1
# Reference solution: only for validating the task.
def tobbi_szorzata(xs):
    out = [1] * len(xs)
    p = 1
    for i, x in enumerate(xs):
        out[i] = p
        p *= x
    p = 1
    for i in range(len(xs) - 1, -1, -1):
        out[i] *= p
        p *= xs[i]
    return out
