# AURI-CANARY-4031638c-818e-5560-bb7c-5b852e19d921
# Reference solution: only for validating the task.
def intervallumok(iv):
    out = []
    for a, b in sorted(iv):
        if a > b:
            raise ValueError((a, b))
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
