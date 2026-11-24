# AURI-CANARY-e1c4bca5-d440-5835-8842-0b701b506ffc
# Reference solution: only for validating the task.
def tokeletes(n):
    if n < 2:
        return False
    s, i = 1, 2
    while i * i <= n:
        if n % i == 0:
            s += i if i * i == n else i + n // i
        i += 1
    return s == n
