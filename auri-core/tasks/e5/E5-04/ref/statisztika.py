def napi(meresek):
    napok = {}
    for d, t in meresek:
        napok.setdefault(d, []).append(t)
    return {d: (min(v), max(v), round(sum(v) / len(v), 2)) for d, v in napok.items()}
