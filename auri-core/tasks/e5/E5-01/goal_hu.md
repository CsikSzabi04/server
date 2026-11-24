Készíts egy kis Python bevásárlólista-projektet a munkakönyvtár gyökerében, két modulból (csak standard könyvtár).
1. `lista.py`: `hozzaad(lista: dict[str, int], nev: str, db: int) -> None` — a nev tételhez db darabot ad (ha még nincs, felveszi); db < 1 esetén `ValueError`. `torol(lista: dict[str, int], nev: str) -> None` — eltávolítja a tételt; ha nincs ilyen, `KeyError`. `osszesen(lista: dict[str, int]) -> int` — az összes darabszám.
2. `formaz.py`: `szoveg(lista: dict[str, int]) -> str` — soronként "név: db", név szerint növekvő sorrendben (a Python alapértelmezett szövegrendezése), a sorok között "\n", a végén nincs sortörés; üres listára üres szöveg.
Írj hozzájuk unittest-teszteket is.
