# AURI-CANARY-6c60b367-61f8-57a7-a28d-4d0193edce34
# Reference solution: only for validating the task.
P = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]


def romai_szam(n):
    if not 1 <= n <= 3999:
        raise ValueError(n)
    out = ''
    for v, r in P:
        while n >= v:
            out += r
            n -= v
    return out
