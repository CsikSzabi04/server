# AURI-CANARY-80fc3a0f-27a3-57eb-82b9-3490214d8931
# Reference solution: only for validating the task.
def primek(n):
    if n < 2:
        return []
    s = [True] * (n + 1)
    s[0] = s[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if s[i]:
            s[i * i::i] = [False] * len(s[i * i::i])
    return [i for i, p in enumerate(s) if p]
