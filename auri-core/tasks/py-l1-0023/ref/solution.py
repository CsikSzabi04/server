# AURI-CANARY-0e0bd4b4-a97e-5c10-9243-874a3884f623
# Reference solution: only for validating the task.
def prim(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True
