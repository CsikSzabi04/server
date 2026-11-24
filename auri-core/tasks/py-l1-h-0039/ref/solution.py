# AURI-CANARY-4da61ba7-7b21-5bc1-bfa2-bbdd71499d40
# Reference solution: only for validating the task.
import re

LEPES = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))


def huszar(mezo):
    if not re.fullmatch(r'[a-h][1-8]', mezo):
        raise ValueError(mezo)
    c, r = ord(mezo[0]) - 97, int(mezo[1])
    return sorted(chr(97 + c + dc) + str(r + dr) for dc, dr in LEPES if 0 <= c + dc < 8 and 1 <= r + dr <= 8)
