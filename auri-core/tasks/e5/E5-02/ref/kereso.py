from index import szavak


def keres(index, lekerdezes):
    ws = szavak(lekerdezes)
    if not ws:
        return []
    return sorted(set.intersection(*[set(index.get(w, [])) for w in ws]))
