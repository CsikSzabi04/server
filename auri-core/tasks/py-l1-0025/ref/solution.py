# AURI-CANARY-24dc8a0e-5dc9-5b07-bcc5-3ca97f3ca1f0
# Reference solution: only for validating the task.
def transzponal(m):
    if any(len(r) != len(m[0]) for r in m):
        raise ValueError('nem téglalap')
    return [list(c) for c in zip(*m, strict=True)]
