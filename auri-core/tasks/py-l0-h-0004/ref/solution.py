# AURI-CANARY-33127245-a122-5ea8-86bc-1da3ec7c079b
# Reference solution: only for validating the task.
def kozepso(s):
    n = len(s)
    a, b = (n - 1) // 2, n // 2 + 1
    return s[a:b] if n else ''
