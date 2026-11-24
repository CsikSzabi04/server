# AURI-CANARY-6d139bcb-7db7-57c9-ab7d-93fdba493bea
# Reference solution: only for validating the task.
import re


def isbn10_ervenyes(s):
    t = s.replace('-', '')
    if not re.fullmatch(r'[0-9]{9}[0-9X]', t):
        return False
    d = [10 if c == 'X' else int(c) for c in t]
    return sum((10 - i) * x for i, x in enumerate(d)) % 11 == 0
