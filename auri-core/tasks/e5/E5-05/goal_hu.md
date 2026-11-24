Készíts egy kis Python szóstatisztika-projektet a munkakönyvtár gyökerében, három modulból (csak standard könyvtár).
1. `szamlalo.py`: `szamol(szoveg: str) -> dict[str, int]` — a `str.split()` szerinti szavak előfordulásai kisbetűsítve; minden szó elejéről és végéről levágja a `.,!?;:` írásjeleket, és ami így üres lesz, kimarad.
2. `top.py`: `top(szamok: dict[str, int], n: int) -> list[tuple[str, int]]` — az n leggyakoribb szó (szó, darab) párokként, darabszám szerint csökkenő, egyenlőségnél szó szerint növekvő sorrendben; n ≤ 0 esetén üres lista.
3. `main.py`: `futtat(szoveg: str, n: int) -> str` — a szöveg top n szava soronként "szó: darab" alakban, a sorok között "\n", a végén nincs sortörés.
Írj hozzájuk unittest-teszteket is.
