# Reference solution: only for validating the task (green on visible + hidden tests).
_MULTI = ("dzs", "cs", "dz", "gy", "ly", "ny", "sz", "ty", "zs")  # "dzs" first: it beats "dz"


def monogram(nev: str) -> str:
    parts: list[str] = []
    for word in nev.split():
        low = word.lower()
        head = next((m for m in _MULTI if low.startswith(m)), low[0])
        parts.append(head[0].upper() + head[1:] + ".")
    return " ".join(parts)
