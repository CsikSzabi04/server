# AURI-CANARY-8a54431f-3a1b-5c4f-a310-b56feb209d18
# Reference solution: only for validating the task.
import re


def taj_ervenyes(s):
    if not re.fullmatch(r'\d{9}|\d{3} \d{3} \d{3}', s):
        return False
    d = [int(c) for c in s if c != ' ']
    return sum(x * (3 if i % 2 == 0 else 7) for i, x in enumerate(d[:8])) % 10 == d[8]
