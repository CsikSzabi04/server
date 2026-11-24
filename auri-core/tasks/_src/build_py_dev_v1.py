"""Generator for the aurikod-hu v1 `dev` split, Python part (40 tasks, L0–L1). Owner: AI-2.

Run:  .venv\\Scripts\\python.exe tasks\\_src\\build_py_dev_v1.py     (rewrites tasks/py-l0-*, py-l1-0004…0031)
Each task → 06/08 §1 layout: task.yaml, tests/test_visible.py, tests/test_hidden.py, ref/solution.py.
Tests are table-driven `unittest` (stdlib only: the S0 sandbox has no pytest/hypothesis) and print the
call with its input on failure (msg=). Canary: deterministic uuid5 per task id (09 §8.2).
"""

from __future__ import annotations

import pprint
import textwrap
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("6f1c2a10-6b1e-4c33-9a57-a1b2c3d40001")
V = "ValueError"

# (level, name, topics, family, title, prompt, signature, ref, visible, hidden, errors, extra_hidden)
T: list[tuple] = []


def task(level, name, topics, family, title, prompt, sig, ref, visible, hidden, errors=(), extra="", vis_errors=()):
    T.append((level, name, topics, family, title, prompt, sig, ref, visible, hidden, list(errors), extra, list(vis_errors)))


# ── L0 ────────────────────────────────────────────────────────────────────────
task(0, "paros_szamok", ["py.basics", "py.collections"], "filter", "Páros számok",
     "Írj `paros_szamok(xs: list[int]) -> list[int]` függvényt, amely a lista páros elemeit adja vissza az eredeti sorrendben. A 0 és a negatív páros számok is párosak.",
     "def paros_szamok(xs: list[int]) -> list[int]", "def paros_szamok(xs):\n    return [x for x in xs if x % 2 == 0]\n",
     [(([1, 2, 3, 4],), [2, 4]), (([],), [])], [(([-2, -1, 0, 7],), [-2, 0]), (([5, 5, 6, 6],), [6, 6]), (([1, 3],), [])])
task(0, "negyzetosszeg", ["py.basics"], "sum-series", "Négyzetösszeg",
     "Írj `negyzetosszeg(n: int) -> int` függvényt: 1² + 2² + … + n². Ha n ≤ 0, az eredmény 0.",
     "def negyzetosszeg(n: int) -> int", "def negyzetosszeg(n):\n    return sum(i * i for i in range(1, n + 1))\n",
     [((3,), 14), ((0,), 0)], [((1,), 1), ((10,), 385), ((-5,), 0), ((100,), 338350)])
task(0, "forditott", ["py.strings"], "str-reverse", "Fordított szöveg",
     "Írj `forditott(s: str) -> str` függvényt, amely a szöveget karakterenként visszafelé adja vissza.",
     "def forditott(s: str) -> str", "def forditott(s):\n    return s[::-1]\n",
     [(("alma",), "amla"), (("",), "")], [(("árvíztűrő",), "őrűtzívrá"), (("ab cd",), "dc ba"), (("x",), "x")])
task(0, "max_index", ["py.collections"], "argmax", "A legnagyobb elem indexe",
     "Írj `max_index(xs: list[int]) -> int` függvényt, amely a legnagyobb elem ELSŐ előfordulásának indexét adja vissza; üres listára -1-et.",
     "def max_index(xs: list[int]) -> int", "def max_index(xs):\n    return xs.index(max(xs)) if xs else -1\n",
     [(([1, 5, 3],), 1), (([],), -1)], [(([7, 7, 2],), 0), (([-3, -1, -2],), 1), (([0],), 0), (([1, 2, 3, 3],), 2)])
task(0, "szamjegyosszeg", ["py.basics"], "digits", "Számjegyösszeg",
     "Írj `szamjegyosszeg(n: int) -> int` függvényt, amely n abszolút értékének számjegyösszegét adja vissza.",
     "def szamjegyosszeg(n: int) -> int", "def szamjegyosszeg(n):\n    return sum(int(d) for d in str(abs(n)))\n",
     [((123,), 6), ((0,), 0)], [((-456,), 15), ((9999,), 36), ((10**12,), 1)])
task(0, "szavak_szama", ["py.strings"], "word-count", "Szavak száma",
     "Írj `szavak_szama(s: str) -> int` függvényt, amely a `str.split()` szerinti szavak számát adja vissza.",
     "def szavak_szama(s: str) -> int", "def szavak_szama(s):\n    return len(s.split())\n",
     [(("alma körte",), 2), (("",), 0)], [(("  sok   szóköz  ",), 2), (("egy\tkettő\nhárom",), 3), (("szó",), 1)])
task(0, "celsius_fahrenheit", ["py.basics"], "unit-convert", "Celsius → Fahrenheit",
     "Írj `celsius_fahrenheit(c: float) -> float` függvényt: F = C · 9/5 + 32, egy tizedesre kerekítve (`round(x, 1)`).",
     "def celsius_fahrenheit(c: float) -> float", "def celsius_fahrenheit(c):\n    return round(c * 9 / 5 + 32, 1)\n",
     [((0,), 32.0), ((100,), 212.0)], [((-40,), -40.0), ((37,), 98.6), ((36.6,), 97.9), ((-273.15,), -459.7)])
task(0, "egyedi", ["py.collections"], "dedupe", "Ismétlődések nélkül",
     "Írj `egyedi(xs: list[int]) -> list[int]` függvényt, amely a lista elemeit ismétlődés nélkül adja vissza, az első előfordulás sorrendjében.",
     "def egyedi(xs: list[int]) -> list[int]", "def egyedi(xs):\n    return list(dict.fromkeys(xs))\n",
     [(([3, 1, 3, 2, 1],), [3, 1, 2])], [(([],), []), (([5, 5, 5],), [5]), (([1, 2, 3],), [1, 2, 3]), (([-1, 0, -1, 0],), [-1, 0])])
task(0, "nagybetus_szavak", ["py.strings"], "filter-words", "Nagybetűs szavak",
     "Írj `nagybetus_szavak(s: str) -> list[str]` függvényt: a `str.split()` szerinti szavak közül azok, amelyek ELSŐ karaktere nagybetű (`str.isupper()`), az eredeti sorrendben.",
     "def nagybetus_szavak(s: str) -> list[str]", "def nagybetus_szavak(s):\n    return [w for w in s.split() if w[0].isupper()]\n",
     [(("Teszt Elek alma",), ["Teszt", "Elek"])],
     [(("",), []), (("Árvíz és Öböl",), ["Árvíz", "Öböl"]), (("1Alma Bé",), ["Bé"]), (("ALMA körte",), ["ALMA"])])
task(0, "atlag", ["py.basics"], "mean", "Átlag",
     "Írj `atlag(xs: list[float]) -> float | None` függvényt: a számtani közép két tizedesre kerekítve (`round(x, 2)`); üres listára `None`.",
     "def atlag(xs: list[float]) -> float | None", "def atlag(xs):\n    return round(sum(xs) / len(xs), 2) if xs else None\n",
     [(([1, 2, 3, 4],), 2.5), (([],), None)], [(([5],), 5.0), (([1, 2],), 1.5), (([1, 1, 2],), 1.33), (([-1.5, 1.5],), 0.0)])
task(0, "fizzbuzz", ["py.basics"], "fizzbuzz", "FizzBuzz",
     "Írj `fizzbuzz(n: int) -> list[str]` függvényt az 1..n számokra: 3-mal osztható → \"Fizz\", 5-tel → \"Buzz\", mindkettővel → \"FizzBuzz\", különben a szám szövegként. n ≤ 0 → üres lista.",
     "def fizzbuzz(n: int) -> list[str]",
     "def fizzbuzz(n):\n    return ['FizzBuzz' if i % 15 == 0 else 'Fizz' if i % 3 == 0 else 'Buzz' if i % 5 == 0 else str(i) for i in range(1, n + 1)]\n",
     [((5,), ["1", "2", "Fizz", "4", "Buzz"])],
     [((0,), []), ((1,), ["1"]), ((15,), ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"])])
task(0, "szorzotabla", ["py.collections"], "table", "Szorzótábla",
     "Írj `szorzotabla(n: int) -> list[list[int]]` függvényt: n×n-es szorzótábla, az i. sor (1-től) `[i*1, i*2, …, i*n]`. n ≤ 0 → üres lista.",
     "def szorzotabla(n: int) -> list[list[int]]", "def szorzotabla(n):\n    return [[i * j for j in range(1, n + 1)] for i in range(1, n + 1)]\n",
     [((2,), [[1, 2], [2, 4]])], [((0,), []), ((1,), [[1]]), ((3,), [[1, 2, 3], [2, 4, 6], [3, 6, 9]]), ((-1,), [])])

# ── L1 ────────────────────────────────────────────────────────────────────────
task(1, "palindrom", ["py.strings"], "palindrome", "Palindrom",
     "Írj `palindrom(s: str) -> bool` függvényt. Csak a betűket és számjegyeket (`str.isalnum()`) vedd figyelembe, kis- és nagybetűtől függetlenül (`str.casefold()`); az ékezetes betű MÁS betű, mint az ékezet nélküli. Az üres szöveg palindrom.",
     "def palindrom(s: str) -> bool", "def palindrom(s):\n    t = [c.casefold() for c in s if c.isalnum()]\n    return t == t[::-1]\n",
     [(("Indul a görög aludni",), True), (("alma",), False)],
     [(("",), True), (("Géza, kék az ég!",), True), (("Ab1ba",), True), (("ége",), False), (("12321",), True), (("12 3",), False), (("!!!",), True)])
task(1, "romai_ertek", ["py.strings", "x.algo"], "roman", "Római szám értéke",
     "Írj `romai_ertek(s: str) -> int` függvényt, amely egy érvényes római szám (I, V, X, L, C, D, M, kivonásos írásmóddal, pl. IV, IX, XL, CM) értékét adja vissza. Kisbetűt is fogadj el. Üres szövegre vagy más karakterre dobj `ValueError`-t.",
     "def romai_ertek(s: str) -> int",
     "V = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n\n\ndef romai_ertek(s):\n    s = s.upper()\n    if not s or any(c not in V for c in s):\n        raise ValueError(s)\n    total = 0\n    for i, c in enumerate(s):\n        v = V[c]\n        total += -v if i + 1 < len(s) and V[s[i + 1]] > v else v\n    return total\n",
     [(("XIV",), 14), (("MCMXCIV",), 1994)], [(("iii",), 3), (("MMMCMXCIX",), 3999), (("XL",), 40), (("CDXLIV",), 444), (("I",), 1)],
     [(("",), V), (("XIIZ",), V), (("12",), V)])
task(1, "romai_szam", ["py.strings", "x.algo"], "roman", "Római szám írása",
     "Írj `romai_szam(n: int) -> str` függvényt, amely 1 ≤ n ≤ 3999 számot a szokásos legrövidebb római alakban adja vissza (kivonásos írásmóddal: IV, IX, XL, XC, CD, CM). Tartományon kívül dobj `ValueError`-t.",
     "def romai_szam(n: int) -> str",
     "P = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]\n\n\ndef romai_szam(n):\n    if not 1 <= n <= 3999:\n        raise ValueError(n)\n    out = ''\n    for v, r in P:\n        while n >= v:\n            out += r\n            n -= v\n    return out\n",
     [((14,), "XIV"), ((1994,), "MCMXCIV")], [((1,), "I"), ((4,), "IV"), ((3999,), "MMMCMXCIX"), ((444,), "CDXLIV"), ((90,), "XC")],
     [((0,), V), ((4000,), V), ((-5,), V)])
task(1, "darabol", ["py.collections"], "chunk", "Darabolás",
     "Írj `darabol(xs: list, size: int) -> list[list]` függvényt: a lista egymást követő, `size` hosszú darabjai; az utolsó darab lehet rövidebb. `size < 1` esetén dobj `ValueError`-t.",
     "def darabol(xs: list, size: int) -> list[list]",
     "def darabol(xs, size):\n    if size < 1:\n        raise ValueError(size)\n    return [xs[i:i + size] for i in range(0, len(xs), size)]\n",
     [(([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])], [(([], 3), []), (([1, 2], 5), [[1, 2]]), (([1, 2, 3], 1), [[1], [2], [3]]), (([1, 2, 3, 4], 2), [[1, 2], [3, 4]])],
     [(([1], 0), V), (([1], -2), V)])
task(1, "kilapit", ["py.collections", "x.algo"], "flatten", "Kilapítás",
     "Írj `kilapit(xs: list) -> list` függvényt: tetszőleges mélységben egymásba ágyazott listák elemei egyetlen listában, balról jobbra. Csak a `list` típust bontsd ki (egy tuple vagy szöveg elem marad).",
     "def kilapit(xs: list) -> list",
     "def kilapit(xs):\n    out = []\n    for x in xs:\n        if isinstance(x, list):\n            out.extend(kilapit(x))\n        else:\n            out.append(x)\n    return out\n",
     [(([1, [2, [3, 4]], 5],), [1, 2, 3, 4, 5])],
     [(([],), []), (([[[]]],), []), (([1, (2, 3), [4]],), [1, (2, 3), 4]), (([["a"], "bc"],), ["a", "bc"]), (([[[[[1]]]]],), [1])])
task(1, "rle_kodol", ["py.strings"], "rle", "Futáshossz-kódolás",
     "Írj `rle_kodol(s: str) -> str` függvényt: az egymást követő azonos karakterek helyére darabszám + karakter kerül, pl. \"aaabcc\" → \"3a1b2c\". Üres szövegre üres szöveg.",
     "def rle_kodol(s: str) -> str",
     "from itertools import groupby\n\n\ndef rle_kodol(s):\n    return ''.join(f'{len(list(g))}{c}' for c, g in groupby(s))\n",
     [(("aaabcc",), "3a1b2c")], [(("",), ""), (("a",), "1a"), (("aaaaaaaaaaaa",), "12a"), (("abab",), "1a1b1a1b"), (("őőű  ",), "2ő1ű2 ")])
task(1, "rle_dekodol", ["py.strings", "py.errors"], "rle", "Futáshossz-visszafejtés",
     "Írj `rle_dekodol(s: str) -> str` függvényt, amely a \"<darabszám><karakter>\" párok sorozatát (pl. \"3a1b2c\" → \"aaabcc\") visszafejti. A darabszám egy vagy több számjegy, a karakter bármi, ami nem számjegy. Üres szövegre üres szöveg. Hibás formátumra (hiányzó darabszám vagy karakter, 0 darabszám) dobj `ValueError`-t.",
     "def rle_dekodol(s: str) -> str",
     "import re\n\n\ndef rle_dekodol(s):\n    parts = re.findall(r'(\\d+)(\\D)', s)\n    if ''.join(n + c for n, c in parts) != s or any(int(n) == 0 for n, _ in parts):\n        raise ValueError(s)\n    return ''.join(c * int(n) for n, c in parts)\n",
     [(("3a1b2c",), "aaabcc")], [(("",), ""), (("12a",), "aaaaaaaaaaaa"), (("2ő1 ",), "őő "), (("1a1b1a",), "aba")],
     [(("a",), V), (("3",), V), (("0a",), V), (("2a3",), V)])
task(1, "osszefesul", ["py.collections", "x.algo"], "merge", "Rendezett listák összefésülése",
     "Írj `osszefesul(a: list[int], b: list[int]) -> list[int]` függvényt, amely két növekvő listát egy növekvő listává fésül össze; az ismétlődések megmaradnak.",
     "def osszefesul(a: list[int], b: list[int]) -> list[int]",
     "def osszefesul(a, b):\n    i = j = 0\n    out = []\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            out.append(a[i])\n            i += 1\n        else:\n            out.append(b[j])\n            j += 1\n    return out + a[i:] + b[j:]\n",
     [(([1, 3, 5], [2, 4]), [1, 2, 3, 4, 5])], [(([], []), []), (([], [1]), [1]), (([1, 1], [1]), [1, 1, 1]), (([-5, 0], [-6, 10]), [-6, -5, 0, 10])])
task(1, "binaris_kereses", ["x.algo"], "bsearch", "Bináris keresés",
     "Írj `binaris_kereses(xs: list[int], x: int) -> int` függvényt: egy növekvő (ismétlődést tartalmazható) listában x LEGBALOLDALIBB előfordulásának indexe, ha nincs benne: -1.",
     "def binaris_kereses(xs: list[int], x: int) -> int",
     "from bisect import bisect_left\n\n\ndef binaris_kereses(xs, x):\n    i = bisect_left(xs, x)\n    return i if i < len(xs) and xs[i] == x else -1\n",
     [(([1, 3, 5, 7], 5), 2), (([1, 3], 4), -1)],
     [(([], 1), -1), (([2, 2, 2], 2), 0), (([1, 2, 2, 3], 2), 1), (([1], 1), 0), (([0, 2, 4, 6, 8, 10], 10), 5), (([1, 3], 0), -1)])
task(1, "anagramma", ["py.strings", "py.collections"], "anagram", "Anagramma",
     "Írj `anagramma(a: str, b: str) -> bool` függvényt: a két szöveg kis- és nagybetűtől (`str.casefold()`) és a szóköz jellegű karakterektől (`str.isspace()`) eltekintve ugyanazokból a karakterekből áll-e, ugyanannyiszor.",
     "def anagramma(a: str, b: str) -> bool",
     "from collections import Counter\n\n\ndef anagramma(a, b):\n    def k(s):\n        return Counter(c for c in s.casefold() if not c.isspace())\n    return k(a) == k(b)\n",
     [(("Listen", "Silent"), True), (("alma", "körte"), False)],
     [(("", ""), True), (("a b", "ba"), True), (("aab", "abb"), False), (("Árvíz", "zívrá"), True), (("ab", "ab "), True), (("alma", "lama"), True)])
task(1, "statisztika", ["py.strings", "py.collections"], "char-class", "Karakterstatisztika",
     "Írj `statisztika(s: str) -> dict[str, int]` függvényt, amely mindig a \"betu\", \"szamjegy\", \"szokoz\", \"egyeb\" kulcsokkal tér vissza: betű = `str.isalpha()`, számjegy = `str.isdigit()`, szóköz = `str.isspace()`, egyéb = minden más karakter.",
     "def statisztika(s: str) -> dict[str, int]",
     "def statisztika(s):\n    d = {'betu': 0, 'szamjegy': 0, 'szokoz': 0, 'egyeb': 0}\n    for c in s:\n        d['betu' if c.isalpha() else 'szamjegy' if c.isdigit() else 'szokoz' if c.isspace() else 'egyeb'] += 1\n    return d\n",
     [(("Alma 12!",), {"betu": 4, "szamjegy": 2, "szokoz": 1, "egyeb": 1})],
     [(("",), {"betu": 0, "szamjegy": 0, "szokoz": 0, "egyeb": 0}), (("é\t\n",), {"betu": 1, "szamjegy": 0, "szokoz": 2, "egyeb": 0}), (("...",), {"betu": 0, "szamjegy": 0, "szokoz": 0, "egyeb": 3})])
task(1, "camel_snake", ["py.strings"], "case-convert", "camelCase → snake_case",
     "Írj `camel_snake(s: str) -> str` függvényt: a szöveg első karakterét kisbetűsítsd; minden további nagybetű elé tegyél egy `_` jelet, és kisbetűsítsd (pl. \"parseForintValue\" → \"parse_forint_value\", \"HTTP\" → \"h_t_t_p\"). Minden más karakter változatlan.",
     "def camel_snake(s: str) -> str",
     "def camel_snake(s):\n    return ''.join(('_' + c.lower()) if i and c.isupper() else c.lower() if i == 0 else c for i, c in enumerate(s))\n",
     [(("parseForintValue",), "parse_forint_value")], [(("",), ""), (("alma",), "alma"), (("Alma",), "alma"), (("HTTP",), "h_t_t_p"), (("aB",), "a_b"), (("x1Y",), "x1_y")])
task(1, "snake_camel", ["py.strings"], "case-convert", "snake_case → camelCase",
     "Írj `snake_camel(s: str) -> str` függvényt: az aláhúzással elválasztott részekből camelCase szöveg; az első rész csupa kisbetű, a többi `str.capitalize()` szerint nagy kezdőbetűs. Az üres részeket (többszörös, kezdő vagy záró aláhúzás) hagyd ki.",
     "def snake_camel(s: str) -> str",
     "def snake_camel(s):\n    p = [x for x in s.split('_') if x]\n    return (p[0].lower() + ''.join(x.capitalize() for x in p[1:])) if p else ''\n",
     [(("parse_forint_value",), "parseForintValue")], [(("",), ""), (("alma",), "alma"), (("__a__b_",), "aB"), (("HELLO_WORLD",), "helloWorld"), (("x_1y",), "x1y")])
task(1, "taj_ervenyes", ["py.strings", "x.algo"], "checksum", "TAJ-szám ellenőrzése",
     "Írj `taj_ervenyes(s: str) -> bool` függvényt. Érvényes a TAJ-szám, ha pontosan 9 számjegy, vagy \"ddd ddd ddd\" alakú (egy-egy szóközzel), és az első 8 számjegy súlyozott összegének (súlyok sorban: 3, 7, 3, 7, 3, 7, 3, 7) 10-es maradéka egyenlő a 9. számjeggyel. Minden más esetben `False`.",
     "def taj_ervenyes(s: str) -> bool",
     "import re\n\n\ndef taj_ervenyes(s):\n    if not re.fullmatch(r'\\d{9}|\\d{3} \\d{3} \\d{3}', s):\n        return False\n    d = [int(c) for c in s if c != ' ']\n    return sum(x * (3 if i % 2 == 0 else 7) for i, x in enumerate(d[:8])) % 10 == d[8]\n",
     [(("123456788",), True), (("123456789",), False)],
     [(("123 456 788",), True), (("987654322",), True), (("000000000",), True), (("12345678",), False), (("1234567888",), False), (("12345678a",), False), (("123-456-788",), False), (("",), False), (("123  456 788",), False)])
task(1, "idotartam_mp", ["py.strings", "py.errors"], "duration", "Időtartam beolvasása",
     "Írj `idotartam_mp(s: str) -> int` függvényt. A bemenet `<szám>h`, `<szám>m`, `<szám>s` részekből áll, EBBEN a sorrendben, egy-egy szóközzel elválasztva; bármelyik rész elhagyható, de legalább egy kell, és egyik sem ismétlődhet. Az eredmény másodpercben, pl. \"1h 30m\" → 5400. Minden más bemenetre dobj `ValueError`-t.",
     "def idotartam_mp(s: str) -> int",
     "import re\n\nORDER = {'h': (0, 3600), 'm': (1, 60), 's': (2, 1)}\n\n\ndef idotartam_mp(s):\n    total, last = 0, -1\n    for part in s.split(' '):\n        m = re.fullmatch(r'(\\d+)([hms])', part)\n        if not m or ORDER[m.group(2)][0] <= last:\n            raise ValueError(s)\n        last, mult = ORDER[m.group(2)]\n        total += int(m.group(1)) * mult\n    return total\n",
     [(("1h 30m",), 5400), (("45s",), 45)], [(("2h",), 7200), (("1h 1m 1s",), 3661), (("90m",), 5400), (("0s",), 0), (("10m 5s",), 605), (("1h 5s",), 3605)],
     [(("",), V), (("1x",), V), (("30m 1h",), V), (("h",), V), (("1h 1h",), V), (("1h30m",), V)])
task(1, "idotartam_szoveg", ["py.strings", "py.errors"], "duration", "Időtartam szövegesen",
     "Írj `idotartam_szoveg(mp: int) -> str` függvényt: másodpercből \"<ó> óra <p> perc <mp> másodperc\" szöveg, a 0 értékű részek elhagyásával, egy-egy szóközzel (pl. 3661 → \"1 óra 1 perc 1 másodperc\", 60 → \"1 perc\"). 0 → \"0 másodperc\". Negatív bemenetre dobj `ValueError`-t.",
     "def idotartam_szoveg(mp: int) -> str",
     "def idotartam_szoveg(mp):\n    if mp < 0:\n        raise ValueError(mp)\n    if mp == 0:\n        return '0 másodperc'\n    h, r = divmod(mp, 3600)\n    m, s = divmod(r, 60)\n    return ' '.join(f'{v} {n}' for v, n in ((h, 'óra'), (m, 'perc'), (s, 'másodperc')) if v)\n",
     [((3661,), "1 óra 1 perc 1 másodperc"), ((0,), "0 másodperc")],
     [((60,), "1 perc"), ((7200,), "2 óra"), ((59,), "59 másodperc"), ((90061,), "25 óra 1 perc 1 másodperc"), ((3601,), "1 óra 1 másodperc")],
     [((-1,), V)])
task(1, "hossz_szerint", ["py.collections"], "group-by", "Csoportosítás hossz szerint",
     "Írj `hossz_szerint(szavak: list[str]) -> dict[int, list[str]]` függvényt: a kulcs a szó hossza, az érték az ilyen hosszú szavak listája az eredeti sorrendben (ismétlődéssel együtt).",
     "def hossz_szerint(szavak: list[str]) -> dict[int, list[str]]",
     "def hossz_szerint(szavak):\n    d = {}\n    for w in szavak:\n        d.setdefault(len(w), []).append(w)\n    return d\n",
     [((["a", "bb", "c"],), {1: ["a", "c"], 2: ["bb"]})],
     [(([],), {}), ((["alma", "alma"],), {4: ["alma", "alma"]}), ((["", ""],), {0: ["", ""]}), ((["ő", "ab", "x"],), {1: ["ő", "x"], 2: ["ab"]})])
task(1, "forgat", ["py.collections"], "rotate", "Lista forgatása",
     "Írj `forgat(xs: list, k: int) -> list` függvényt: a lista jobbra forgatva k lépéssel (az utolsó elem kerül előre). k lehet negatív (balra forgatás) vagy nagyobb a lista hosszánál. Az eredeti listát NE módosítsd; üres listára üres lista.",
     "def forgat(xs: list, k: int) -> list",
     "def forgat(xs, k):\n    if not xs:\n        return []\n    k %= len(xs)\n    return xs[-k:] + xs[:-k] if k else list(xs)\n",
     [(([1, 2, 3, 4], 1), [4, 1, 2, 3])], [(([], 3), []), (([1, 2, 3], 0), [1, 2, 3]), (([1, 2, 3], 4), [3, 1, 2]), (([1, 2, 3], -1), [2, 3, 1]), (([1], 100), [1])],
     extra="    def test_nem_modosit(self) -> None:\n        xs = [1, 2, 3]\n        forgat(xs, 1)\n        self.assertEqual(xs, [1, 2, 3], msg='forgat(xs, 1) után az xs változatlan')\n")
task(1, "pascal_sor", ["x.algo"], "pascal", "Pascal-háromszög sora",
     "Írj `pascal_sor(n: int) -> list[int]` függvényt: a Pascal-háromszög n. sora (0-tól számozva: 0 → [1], 2 → [1, 2, 1]). Negatív n esetén dobj `ValueError`-t.",
     "def pascal_sor(n: int) -> list[int]",
     "def pascal_sor(n):\n    if n < 0:\n        raise ValueError(n)\n    row = [1]\n    for _ in range(n):\n        row = [a + b for a, b in zip([0, *row], [*row, 0], strict=True)]\n    return row\n",
     [((0,), [1]), ((4,), [1, 4, 6, 4, 1])], [((1,), [1, 1]), ((2,), [1, 2, 1]), ((10,), [1, 10, 45, 120, 210, 252, 210, 120, 45, 10, 1])], [((-1,), V)])
task(1, "prim", ["x.algo"], "prime", "Prímszám-e",
     "Írj `prim(n: int) -> bool` függvényt, amely eldönti, hogy n prímszám-e. 2-nél kisebb számok (a negatívak is) nem prímek.",
     "def prim(n: int) -> bool",
     "def prim(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n    return True\n",
     [((7,), True), ((8,), False)], [((0,), False), ((1,), False), ((2,), True), ((-7,), False), ((97,), True), ((91,), False), ((7919,), True), ((1000003,), True), ((1000001,), False)])
task(1, "primek", ["x.algo"], "prime", "Prímek n-ig",
     "Írj `primek(n: int) -> list[int]` függvényt: az n-nél nem nagyobb prímszámok növekvő sorrendben (n < 2 → üres lista).",
     "def primek(n: int) -> list[int]",
     "def primek(n):\n    if n < 2:\n        return []\n    s = [True] * (n + 1)\n    s[0] = s[1] = False\n    for i in range(2, int(n ** 0.5) + 1):\n        if s[i]:\n            s[i * i::i] = [False] * len(s[i * i::i])\n    return [i for i, p in enumerate(s) if p]\n",
     [((10,), [2, 3, 5, 7])], [((1,), []), ((2,), [2]), ((-5,), []), ((30,), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])],
     extra="    def test_sok(self) -> None:\n        self.assertEqual(len(primek(10000)), 1229, msg='len(primek(10000))')\n")
task(1, "transzponal", ["py.collections", "py.errors"], "matrix", "Mátrix transzponálása",
     "Írj `transzponal(m: list[list[int]]) -> list[list[int]]` függvényt, amely egy téglalap alakú mátrix (sorok listája) transzponáltját adja vissza; üres listára üres listát. Ha a sorok hossza eltér, dobj `ValueError`-t.",
     "def transzponal(m: list[list[int]]) -> list[list[int]]",
     "def transzponal(m):\n    if any(len(r) != len(m[0]) for r in m):\n        raise ValueError('nem téglalap')\n    return [list(c) for c in zip(*m, strict=True)]\n",
     [(([[1, 2, 3], [4, 5, 6]],), [[1, 4], [2, 5], [3, 6]])], [(([],), []), (([[1]],), [[1]]), (([[1, 2]],), [[1], [2]]), (([[1], [2]],), [[1, 2]])],
     [(([[1, 2], [3]],), V)])
task(1, "masodik_legnagyobb", ["py.collections"], "order-stat", "Második legnagyobb",
     "Írj `masodik_legnagyobb(xs: list[int]) -> int | None` függvényt: a második legnagyobb KÜLÖNBÖZŐ érték; ha nincs legalább két különböző érték, `None`.",
     "def masodik_legnagyobb(xs: list[int]) -> int | None",
     "def masodik_legnagyobb(xs):\n    u = sorted(set(xs))\n    return u[-2] if len(u) >= 2 else None\n",
     [(([3, 1, 4, 4],), 3), (([5, 5],), None)], [(([],), None), (([1],), None), (([-1, -2],), -2), (([1, 2, 3, 4, 5],), 4), (([10, 10, 9, 9],), 9)])
task(1, "sortores", ["py.strings"], "wrap", "Sortörés",
     "Írj `sortores(szoveg: str, szelesseg: int) -> list[str]` függvényt: a `str.split()` szerinti szavakat sorokba tördeli; egy sorba balról jobbra annyi szó kerül (egy-egy szóközzel), amennyi `szelesseg` karakterbe belefér. A `szelesseg`-nél hosszabb szó külön sorba kerül, csonkítás nélkül. Üres szövegre üres lista; `szelesseg < 1` esetén dobj `ValueError`-t.",
     "def sortores(szoveg: str, szelesseg: int) -> list[str]",
     "def sortores(szoveg, szelesseg):\n    if szelesseg < 1:\n        raise ValueError(szelesseg)\n    sorok, cur = [], ''\n    for w in szoveg.split():\n        if cur and len(cur) + 1 + len(w) <= szelesseg:\n            cur += ' ' + w\n        else:\n            if cur:\n                sorok.append(cur)\n            cur = w\n    if cur:\n        sorok.append(cur)\n    return sorok\n",
     [(("alma körte szilva", 10), ["alma körte", "szilva"])],
     [(("", 5), []), (("a b c", 1), ["a", "b", "c"]), (("a b c", 3), ["a b", "c"]), (("hosszúszó x", 4), ["hosszúszó", "x"]), (("  több   szóköz  ", 20), ["több szóköz"]), (("ab cd", 5), ["ab cd"])],
     [(("x", 0), V)])
task(1, "zarojelek", ["x.ds", "x.algo"], "brackets", "Zárójelek",
     "Írj `zarojelek(s: str) -> bool` függvényt: a `()`, `[]`, `{}` zárójelek helyesen párosítottak és egymásba ágyazottak-e. Minden más karaktert hagyj figyelmen kívül.",
     "def zarojelek(s: str) -> bool",
     "def zarojelek(s):\n    st, pair = [], {')': '(', ']': '[', '}': '{'}\n    for c in s:\n        if c in '([{':\n            st.append(c)\n        elif c in pair and (not st or st.pop() != pair[c]):\n            return False\n    return not st\n",
     [(("([]{})",), True), (("(]",), False)],
     [(("",), True), (("a(b)c",), True), (("(",), False), ((")(",), False), (("([)]",), False), (("{[()()]}",), True), (("((x)",), False)])
task(1, "telefonszam", ["py.strings", "py.errors"], "normalize", "Telefonszám egységesítése",
     "Írj `telefonszam(s: str) -> str` függvényt, amely egy magyar mobilszámot \"+36\" + 9 számjegy alakra hoz (pl. \"06 30 123 4567\" → \"+36301234567\"). A szóközt, a kötőjelet, a perjelet és a zárójeleket hagyd el; ezután a szám `+36`, `36` vagy `06` előtaggal kezdődjön, és utána pontosan 9 számjegy álljon. Minden más esetben dobj `ValueError`-t.",
     "def telefonszam(s: str) -> str",
     "import re\n\n\ndef telefonszam(s):\n    t = re.sub(r'[ \\-/()]', '', s)\n    m = re.fullmatch(r'(?:\\+36|36|06)(\\d{9})', t)\n    if not m:\n        raise ValueError(s)\n    return '+36' + m.group(1)\n",
     [(("06 30 123 4567",), "+36301234567")],
     [(("+36301234567",), "+36301234567"), (("36-20-765-4321",), "+36207654321"), (("(06) 70/111-2222",), "+36701112222"), (("06301234567",), "+36301234567")],
     [(("",), V), (("30 123 4567",), V), (("06 30 123 456",), V), (("+3630123456a",), V), (("+36 30 123 45678",), V)])
task(1, "datum", ["py.strings", "py.errors"], "date-parse", "Magyar dátum",
     "Írj `datum(s: str) -> tuple[int, int, int]` függvényt, amely egy \"ÉÉÉÉ.HH.NN.\" alakú dátumot (év, hónap, nap) hármassá alakít. Az év 4 számjegy; a hónap és a nap egy- vagy kétjegyű; minden pont után állhat egy szóköz (\"2026. 11. 21.\"); a záró pont kötelező. Ellenőrizd, hogy a dátum létezik (szökőév: osztható 4-gyel, de a 100-zal oszthatók közül csak a 400-zal oszthatók). Minden más esetben dobj `ValueError`-t.",
     "def datum(s: str) -> tuple[int, int, int]",
     "import re\n\n\ndef datum(s):\n    m = re.fullmatch(r'(\\d{4})\\. ?(\\d{1,2})\\. ?(\\d{1,2})\\.', s)\n    if not m:\n        raise ValueError(s)\n    y, mo, d = map(int, m.groups())\n    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)\n    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n    if not 1 <= mo <= 12 or not 1 <= d <= days[mo - 1]:\n        raise ValueError(s)\n    return (y, mo, d)\n",
     [(("2026.11.21.",), (2026, 11, 21)), (("2026. 11. 21.",), (2026, 11, 21))],
     [(("2024.2.29.",), (2024, 2, 29)), (("2000.02.29.",), (2000, 2, 29)), (("1999.12.31.",), (1999, 12, 31))],
     [(("2023.02.29.",), V), (("1900.02.29.",), V), (("2026.13.01.",), V), (("2026.11.31.",), V), (("2026.11.21",), V), (("2026-11-21",), V), (("",), V), (("2026.00.10.",), V)])
task(1, "maganhangzok", ["py.strings"], "char-count", "Magánhangzók",
     "Írj `maganhangzok(s: str) -> int` függvényt, amely megszámolja a magyar magánhangzókat (a á e é i í o ó ö ő u ú ü ű), kis- és nagybetűtől függetlenül.",
     "def maganhangzok(s: str) -> int", "def maganhangzok(s):\n    return sum(c in 'aáeéiíoóöőuúüű' for c in s.lower())\n",
     [(("Teszt Elek",), 3), (("",), 0)], [(("ÁRVÍZTŰRŐ TÜKÖRFÚRÓGÉP",), 9), (("xyz",), 0), (("aeiou",), 5), (("Öböl",), 2)])


# ── writer ────────────────────────────────────────────────────────────────────

TEST_TMPL = '''# {canary}
{header}import copy
import unittest

from solution import {fn}

CASES = {cases}
{errors_def}

def _call(args: tuple) -> str:
    return "{fn}(" + ", ".join(map(repr, args)) + ")"


class Test{kind}(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual({fn}(*copy.deepcopy(args)), want, msg=_call(args))
{errors_test}{extra}

if __name__ == "__main__":
    unittest.main()
'''

ERR_TEST = '''
    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                {fn}(*copy.deepcopy(args))
'''


def fmt(obj: object) -> str:
    return pprint.pformat(obj, width=110, sort_dicts=False)


def test_file(canary: str, fn: str, kind: str, cases: list, errors: list, extra: str) -> str:
    header = "# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.\n" if kind == "Hidden" else ""
    header += "import builtins\n" if errors else ""
    return TEST_TMPL.format(
        canary=canary, header=header, fn=fn, cases=fmt(cases), kind=kind,
        errors_def=f"ERRORS = {fmt(errors)}\n" if errors else "",
        errors_test=ERR_TEST.format(fn=fn) if errors else "", extra=("\n" + extra) if extra else "",
    )


def build() -> list[str]:
    counters = {0: 0, 1: 3}  # py-l1-0001…0003 are the P0-mini practice tasks
    ids = []
    for level, fn, topics, family, title, prompt, sig, ref, visible, hidden, errors, extra, vis_errors in T:
        counters[level] += 1
        tid = f"py-l{level}-{counters[level]:04d}"
        canary = f"AURI-CANARY-{uuid.uuid5(NS, 'aurikod-hu-v1/' + tid)}"
        d = ROOT / tid
        (d / "tests").mkdir(parents=True, exist_ok=True)
        (d / "ref").mkdir(exist_ok=True)
        yaml = (f"# {canary}\nid: {tid}\nlevel: {level}\nlang: py\ntopics: [{', '.join(topics)}]\ntitle_hu: {title}\nprompt_hu: |\n"
                + textwrap.indent(textwrap.fill(prompt, 110, break_long_words=False, break_on_hyphens=False), "  ") + "\n"
                + f"signature: \"{sig}\"\nfiles: {{visible: tests/test_visible.py, hidden: tests/test_hidden.py, reference: ref/solution.py}}\n"
                + f"source: {{kind: own, license: own}}\nlimits: {{wall_s: 20, mem_mb: 512}}\nsplit: dev\nfamily: {family}\n"
                + f"rating: {1000 + 200 * level}\n")
        files = {
            "task.yaml": yaml,
            "tests/test_visible.py": test_file(canary, fn, "Visible", visible, vis_errors, ""),
            "tests/test_hidden.py": test_file(canary, fn, "Hidden", hidden, errors, extra),
            "ref/solution.py": f"# {canary}\n# Reference solution: only for validating the task.\n{ref}",
        }
        for rel, text in files.items():
            (d / rel).write_text(text, encoding="utf-8", newline="\n")
        ids.append(tid)
    return ids


if __name__ == "__main__":
    out = build()
    print(len(out), "tasks:", out[0], "…", out[-1])
