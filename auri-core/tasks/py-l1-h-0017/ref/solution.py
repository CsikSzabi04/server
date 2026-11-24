# AURI-CANARY-4ec8c631-2174-5e1a-a568-dd387eda0eb3
# Reference solution: only for validating the task.
def kozos_elotag(szavak):
    if not szavak:
        return ''
    p = szavak[0]
    for w in szavak[1:]:
        while not w.startswith(p):
            p = p[:-1]
    return p
