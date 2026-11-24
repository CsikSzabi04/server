# AURI-CANARY-319adfe0-2fec-5687-b7fa-4ba86e12eb92
# Reference solution: only for validating the task.
import re


def rle_dekodol(s):
    parts = re.findall(r'(\d+)(\D)', s)
    if ''.join(n + c for n, c in parts) != s or any(int(n) == 0 for n, _ in parts):
        raise ValueError(s)
    return ''.join(c * int(n) for n, c in parts)
