# AURI-CANARY-fcec98ed-c3c0-5d8b-b4c0-bc2ac0a485d6
# Reference solution: only for validating the task.
def matrix_forgat(m):
    if any(len(r) != len(m[0]) for r in m):
        raise ValueError('nem téglalap')
    return [list(r) for r in zip(*m[::-1], strict=True)]
