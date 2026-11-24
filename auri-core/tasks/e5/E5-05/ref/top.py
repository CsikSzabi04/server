def top(szamok, n):
    return sorted(szamok.items(), key=lambda kv: (-kv[1], kv[0]))[:max(0, n)]
