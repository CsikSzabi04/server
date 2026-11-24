Készíts egy kis Python pénztár-projektet a munkakönyvtár gyökerében, három modulból (csak standard könyvtár).
1. `ar.py`: `brutto(netto: int, afa: int) -> int` — a nettó forintár és az áfakulcs (százalék, pl. 27) alapján a bruttó ár egész forintra kerekítve, a fél forintot felfelé (pl. 50 Ft és 27% → 63,5 → 64). Ha netto < 0 vagy afa < 0, `ValueError`.
2. `kosar.py`: `vegosszeg(tetelek: list[tuple[int, int, int]]) -> int` — a tételek (nettó, áfakulcs, darab) hármasok; a végösszeg a tételenkénti bruttó egységár (az `ar.brutto` szerint) és a darab szorzatának összege.
3. `nyugta.py`: `nyugta(tetelek: list[tuple[int, int, int]]) -> list[str]` — tételenként egy sor "<db> x <bruttó egységár> Ft = <db · bruttó egységár> Ft", a végén egy "ÖSSZESEN: <végösszeg> Ft" sor.
Írj hozzájuk unittest-teszteket is.
