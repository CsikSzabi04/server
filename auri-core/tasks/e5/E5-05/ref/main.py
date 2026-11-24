from szamlalo import szamol
from top import top


def futtat(szoveg, n):
    return "\n".join(f"{w}: {db}" for w, db in top(szamol(szoveg), n))
