# AURI-CANARY-bbb7e7a4-a514-5a6e-ad63-25d70aae5000
# Reference solution: only for validating the task.
def szigetek(terkep):
    h = len(terkep)
    w = len(terkep[0]) if h else 0
    seen = set()
    db = 0
    for r in range(h):
        for c in range(w):
            if terkep[r][c] != '#' or (r, c) in seen:
                continue
            db += 1
            seen.add((r, c))
            stack = [(r, c)]
            while stack:
                y, x = stack.pop()
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < h and 0 <= nx < w and terkep[ny][nx] == '#' and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
    return db
