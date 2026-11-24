# AURI-CANARY-9ea9c482-407f-5ea8-bc8d-ae0f87bd4a84
# Reference solution: only for validating the task.
import re


def hex_szin(s):
    if not re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', s):
        raise ValueError(s)
    h = s[1:]
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
