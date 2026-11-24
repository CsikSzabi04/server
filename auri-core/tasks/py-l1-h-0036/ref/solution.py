# AURI-CANARY-3e2c44de-20ea-59f3-a3d9-5055539751a5
# Reference solution: only for validating the task.
def szo_minta(minta, s):
    w = s.split()
    if len(w) != len(minta):
        return False
    return len(set(minta)) == len(set(w)) == len(set(zip(minta, w, strict=True)))
