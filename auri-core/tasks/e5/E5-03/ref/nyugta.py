from ar import brutto
from kosar import vegosszeg


def nyugta(tetelek):
    sorok = [f"{db} x {brutto(n, a)} Ft = {db * brutto(n, a)} Ft" for n, a, db in tetelek]
    return [*sorok, f"ÖSSZESEN: {vegosszeg(tetelek)} Ft"]
