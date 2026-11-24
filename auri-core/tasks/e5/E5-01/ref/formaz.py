def szoveg(lista):
    return "\n".join(f"{k}: {v}" for k, v in sorted(lista.items()))
