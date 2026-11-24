# AURI-CANARY-5496f464-07ef-5052-bf74-1ea1173273f3
# Reference solution: only for validating the task.
from collections import deque


def racs_ut(racs):
    if not racs or not racs[0]:
        return -1
    h, w = len(racs), len(racs[0])
    if racs[0][0] == '#' or racs[h - 1][w - 1] == '#':
        return -1
    dist = {(0, 0): 0}
    q = deque([(0, 0)])
    while q:
        r, c = q.popleft()
        if (r, c) == (h - 1, w - 1):
            return dist[(r, c)]
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < h and 0 <= nc < w and racs[nr][nc] == '.' and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return -1
