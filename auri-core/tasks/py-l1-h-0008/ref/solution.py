# AURI-CANARY-40b5b27d-88e0-5865-b1ce-7e94cda62213
# Reference solution: only for validating the task.
def spiral(m):
    out = []
    m = [list(r) for r in m]
    while m and m[0]:
        out += m.pop(0)
        if m and m[0]:
            for r in m:
                out.append(r.pop())
        if m:
            out += m.pop()[::-1]
        if m and m[0]:
            for r in m[::-1]:
                out.append(r.pop(0))
    return out
