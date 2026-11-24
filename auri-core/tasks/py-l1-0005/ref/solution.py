# AURI-CANARY-629c0c9a-1b1c-5238-b07c-b21c22c89e5e
# Reference solution: only for validating the task.
V = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def romai_ertek(s):
    s = s.upper()
    if not s or any(c not in V for c in s):
        raise ValueError(s)
    total = 0
    for i, c in enumerate(s):
        v = V[c]
        total += -v if i + 1 < len(s) and V[s[i + 1]] > v else v
    return total
