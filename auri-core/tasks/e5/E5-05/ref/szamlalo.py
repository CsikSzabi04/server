def szamol(szoveg):
    out = {}
    for w in szoveg.split():
        t = w.lower().strip(".,!?;:")
        if t:
            out[t] = out.get(t, 0) + 1
    return out
