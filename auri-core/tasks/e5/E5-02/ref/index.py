def szavak(szoveg):
    out, cur = [], ""
    for c in szoveg.lower():
        if c.isalnum():
            cur += c
        elif cur:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def epit(dokumentumok):
    idx = {}
    for doc_id, text in dokumentumok.items():
        for w in set(szavak(text)):
            idx.setdefault(w, []).append(doc_id)
    return {w: sorted(ids) for w, ids in idx.items()}
