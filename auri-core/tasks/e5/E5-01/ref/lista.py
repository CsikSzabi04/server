def hozzaad(lista, nev, db):
    if db < 1:
        raise ValueError(db)
    lista[nev] = lista.get(nev, 0) + db


def torol(lista, nev):
    del lista[nev]


def osszesen(lista):
    return sum(lista.values())
