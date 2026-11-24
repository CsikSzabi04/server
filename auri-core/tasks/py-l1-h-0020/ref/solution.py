# AURI-CANARY-5afdc06c-c900-5603-bcb2-5c528cf717b5
# Reference solution: only for validating the task.
def lepcso(n):
    if n < 0:
        raise ValueError(n)
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a
