from ar import brutto


def vegosszeg(tetelek):
    return sum(brutto(n, a) * db for n, a, db in tetelek)
