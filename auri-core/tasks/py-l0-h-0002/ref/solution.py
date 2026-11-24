# AURI-CANARY-a3249e12-2640-5f04-988a-740ce7a26a09
# Reference solution: only for validating the task.
def faktorialis(n):
    if n < 0:
        raise ValueError(n)
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r
