Készíts egy kis Python jegyzetkereső-projektet a munkakönyvtár gyökerében, két modulból (csak standard könyvtár).
1. `index.py`: `szavak(szoveg: str) -> list[str]` — a kisbetűsített szöveg betűkből és számjegyekből (`str.isalnum()`) álló, összefüggő karaktersorozatai, sorrendben. `epit(dokumentumok: dict[str, str]) -> dict[str, list[str]]` — minden szóhoz azon dokumentum-azonosítók növekvően rendezett, ismétlés nélküli listája, amelyekben a szó előfordul.
2. `kereso.py`: `keres(index: dict[str, list[str]], lekerdezes: str) -> list[str]` — azon dokumentumok növekvően rendezett listája, amelyekben a lekérdezés minden szava (az `index.szavak` szerint) előfordul; ha a lekérdezésben nincs szó, üres lista.
Írj hozzájuk unittest-teszteket is.
