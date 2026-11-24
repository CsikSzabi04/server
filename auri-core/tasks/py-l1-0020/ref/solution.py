# AURI-CANARY-ae90ae24-b59f-570b-8aa5-3a91f504578e
# Reference solution: only for validating the task.
def hossz_szerint(szavak):
    d = {}
    for w in szavak:
        d.setdefault(len(w), []).append(w)
    return d
