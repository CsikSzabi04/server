# AURI-CANARY-e8ae753a-da02-51be-9e5e-50975be794bb
# Reference solution: only for validating the task.
def masodik_legnagyobb(xs):
    u = sorted(set(xs))
    return u[-2] if len(u) >= 2 else None
