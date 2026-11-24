# AURI-CANARY-d30b9687-12b9-5a93-9128-4fb6dd14c4da
# Reference solution: only for validating the task.
def collatz_lepesek(n):
    if n < 1:
        raise ValueError(n)
    k = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        k += 1
    return k
