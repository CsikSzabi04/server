def brutto(netto, afa):
    if netto < 0 or afa < 0:
        raise ValueError((netto, afa))
    return (netto * (100 + afa) + 50) // 100
