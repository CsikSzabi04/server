import re


def beolvas(sorok):
    out = []
    for s in sorok:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (-?\d+(?:\.\d+)?)", s)
        if m:
            out.append((m.group(1), float(m.group(2))))
    return out
