"""Generator for the aurikod-hu v1 `heldout` split: 60 tasks per language (18 × L0, 42 × L1), Python + TS. Owner: AI-2.

FROZEN (06/09 §2, ai_prompts §2/13 + §4/6): only AI-2 and `bench --official` read these files; nobody tunes prompts
on them. Run once:  .venv\\Scripts\\python.exe tasks\\_src\\build_heldout_v1.py
It refuses to overwrite an existing heldout (a new version = new ids + new manifest). Output: tasks/{py,ts}-l{0,1}-h-NNNN/
and the sha256 manifest tasks/_manifest/heldout-v1.json (checked by taskset.verify_heldout and the bench guard).
Problems are disjoint from the dev families; every hidden case checks only behaviour stated in prompt_hu.
"""

from __future__ import annotations

import json
import sys
import textwrap
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from build_py_dev_v1 import NS, ROOT, test_file
from build_ts_dev_v1 import FORBIDDEN, PROMPT_MAP, TEST_TMPL, TOPIC, js

from auri_core import taskset

V = "ValueError"
H: list[dict] = []
EXTRA_MAP = [
    ("(`str.isalpha()`)", "(Unicode betű: `/\\p{L}/u`)"),
    ("s `str.split()` szerinti szavai", "s whitespace (`/\\s+/`) mentén elválasztott, nem üres szavai"),
    ("a szótár kulcsai", "az objektum kulcsai"),
]
FORBIDDEN_H = (*FORBIDDEN, "szótár", "True", "False", "isalpha", "len(")


def h(level, name, topics, family, title, prompt, sig, py, ts, vis, hid, err=()):
    H.append({"level": level, "name": name, "topics": topics, "family": family, "title": title, "prompt": prompt,
              "sig": sig, "py": py, "ts": ts, "vis": vis, "hid": hid, "err": list(err)})


def code(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


# ── L0 (18) ───────────────────────────────────────────────────────────────────
h(0, "paratlan_osszeg", ["py.basics"], "sum-odd", "Páratlan elemek összege",
  "Írj `paratlan_osszeg(xs: list[int]) -> int` függvényt, amely a lista páratlan elemeinek összegét adja vissza (a negatív páratlan számok is számítanak). Üres listára 0.",
  "def paratlan_osszeg(xs: list[int]) -> int", "def paratlan_osszeg(xs):\n    return sum(x for x in xs if x % 2 != 0)\n",
  ("xs: number[]): number", "return xs.filter((x) => x % 2 !== 0).reduce((a, b) => a + b, 0);"),
  [(([1, 2, 3],), 4), (([],), 0)], [(([-3, -2, 5],), 2), (([2, 4, 6],), 0), (([7],), 7), (([-1, -1],), -2)])
h(0, "faktorialis", ["py.basics", "py.errors"], "factorial", "Faktoriális",
  "Írj `faktorialis(n: int) -> int` függvényt: n! (0! = 1). Negatív n-re dobj `ValueError`-t.",
  "def faktorialis(n: int) -> int", code(r'''
    def faktorialis(n):
        if n < 0:
            raise ValueError(n)
        r = 1
        for i in range(2, n + 1):
            r *= i
        return r
  '''),
  ("n: number): number", code(r'''
    if (n < 0) throw new RangeError(String(n));
    let r = 1;
    for (let i = 2; i <= n; i++) r *= i;
    return r;
  ''')),
  [((5,), 120), ((0,), 1)], [((1,), 1), ((10,), 3628800), ((15,), 1307674368000)], [(-1,), (-10,)])
h(0, "elofordulas", ["py.collections"], "count", "Előfordulások száma",
  "Írj `elofordulas(xs: list[int], x: int) -> int` függvényt, amely megszámolja, hányszor szerepel x a listában.",
  "def elofordulas(xs: list[int], x: int) -> int", "def elofordulas(xs, x):\n    return xs.count(x)\n",
  ("xs: number[], x: number): number", "return xs.filter((y) => y === x).length;"),
  [(([1, 2, 1, 3], 1), 2), (([], 5), 0)], [(([0, 0, 0], 0), 3), (([1, 2, 3], 4), 0), (([-1, 1, -1], -1), 2)])
h(0, "kozepso", ["py.strings"], "middle", "Középső karakter",
  "Írj `kozepso(s: str) -> str` függvényt: páratlan hosszú szövegnél a középső karaktert, páros hosszúnál a középső kettőt adja vissza; üres szövegre üres szöveget.",
  "def kozepso(s: str) -> str", code(r'''
    def kozepso(s):
        n = len(s)
        a, b = (n - 1) // 2, n // 2 + 1
        return s[a:b] if n else ''
  '''),
  ("s: string): string", "const n = s.length;\nreturn n === 0 ? '' : s.slice(Math.floor((n - 1) / 2), Math.floor(n / 2) + 1);"),
  [(("alma",), "lm"), (("kerék",), "r")], [(("",), ""), (("x",), "x"), (("ab",), "ab"), (("árvíz",), "v")])
h(0, "szokoev", ["py.basics"], "leap-year", "Szökőév",
  "Írj `szokoev(ev: int) -> bool` függvényt a Gergely-naptár szerint: szökőév, ha osztható 4-gyel, kivéve a 100-zal oszthatókat, de a 400-zal oszthatók mégis szökőévek.",
  "def szokoev(ev: int) -> bool", "def szokoev(ev):\n    return ev % 4 == 0 and (ev % 100 != 0 or ev % 400 == 0)\n",
  ("ev: number): boolean", "return ev % 4 === 0 && (ev % 100 !== 0 || ev % 400 === 0);"),
  [((2024,), True), ((2023,), False)], [((1900,), False), ((2000,), True), ((2100,), False), ((1996,), True)])
h(0, "kezdobetuk", ["py.strings"], "acronym", "Kezdőbetűk",
  'Írj `kezdobetuk(s: str) -> str` függvényt: a `str.split()` szerinti szavak első betűit nagybetűsítve fűzi össze (pl. "magyar tudományos akadémia" → "MTA"). Üres szövegre üres szöveg.',
  "def kezdobetuk(s: str) -> str", "def kezdobetuk(s):\n    return ''.join(w[0].upper() for w in s.split())\n",
  ("s: string): string", "return s.split(/\\s+/).filter(Boolean).map((w) => w[0].toUpperCase()).join('');"),
  [(("magyar tudományos akadémia",), "MTA"), (("",), "")], [(("  öt   ökör ",), "ÖÖ"), (("Egy",), "E"), (("a\tb\nc",), "ABC")])
h(0, "haromszog", ["py.basics"], "triangle", "Háromszög-egyenlőtlenség",
  "Írj `haromszog(a: float, b: float, c: float) -> bool` függvényt: igaz, ha a három oldalhosszból (nem elfajuló) háromszög szerkeszthető, vagyis mindhárom pozitív, és bármely kettő összege szigorúan nagyobb a harmadiknál.",
  "def haromszog(a: float, b: float, c: float) -> bool",
  "def haromszog(a, b, c):\n    return min(a, b, c) > 0 and a + b > c and a + c > b and b + c > a\n",
  ("a: number, b: number, c: number): boolean", "return Math.min(a, b, c) > 0 && a + b > c && a + c > b && b + c > a;"),
  [((3, 4, 5), True), ((1, 2, 3), False)], [((2, 2, 3), True), ((0, 1, 1), False), ((-3, 4, 5), False), ((10, 1, 1), False), ((1.5, 1.5, 2.9), True)])
h(0, "teljes_negyzet", ["py.basics"], "square", "Teljes négyzet",
  "Írj `teljes_negyzet(n: int) -> bool` függvényt: igaz, ha n egy egész szám négyzete (a 0 is az). Negatív n-re hamis.",
  "def teljes_negyzet(n: int) -> bool", "import math\n\n\ndef teljes_negyzet(n):\n    return n >= 0 and math.isqrt(n) ** 2 == n\n",
  ("n: number): boolean", "if (n < 0) return false;\nconst r = Math.round(Math.sqrt(n));\nreturn r * r === n;"),
  [((16,), True), ((15,), False)], [((0,), True), ((-4,), False), ((1000000,), True), ((999999,), False), ((10**12,), True), ((10**12 + 1,), False)])
h(0, "ismetel", ["py.strings"], "repeat", "Ismétlés elválasztóval",
  "Írj `ismetel(s: str, n: int, sep: str) -> str` függvényt, amely az s szöveget n-szer egymás után fűzi, a példányok közé a sep elválasztót téve. Ha n ≤ 0, üres szöveg.",
  "def ismetel(s: str, n: int, sep: str) -> str", "def ismetel(s, n, sep):\n    return sep.join([s] * max(0, n))\n",
  ("s: string, n: number, sep: string): string", "return Array(Math.max(0, n)).fill(s).join(sep);"),
  [(("ab", 3, "-"), "ab-ab-ab"), (("x", 0, ","), "")], [(("x", 1, ","), "x"), (("", 3, "|"), "||"), (("hó", 2, ""), "hóhó"), (("a", -2, "-"), "")])
h(0, "leghosszabb_szo", ["py.strings"], "longest-word", "Leghosszabb szó",
  "Írj `leghosszabb_szo(s: str) -> str` függvényt: a `str.split()` szerinti szavak közül a leghosszabbat adja vissza; egyenlőségnél az elsőt. Ha nincs szó, üres szöveget.",
  "def leghosszabb_szo(s: str) -> str", "def leghosszabb_szo(s):\n    return max(s.split(), key=len, default='')\n",
  ("s: string): string", "let best = '';\nfor (const w of s.split(/\\s+/)) if (w.length > best.length) best = w;\nreturn best;"),
  [(("a kutya ugat",), "kutya"), (("",), "")], [(("egy ketto hat",), "ketto"), (("ab cd",), "ab"), (("  szó  ",), "szó"), (("árvíztűrő tükör",), "árvíztűrő")])
h(0, "kumulalt", ["py.collections"], "prefix-sum", "Futó összeg",
  "Írj `kumulalt(xs: list[int]) -> list[int]` függvényt: az eredmény i. eleme az xs első i+1 elemének összege (pl. [1, 2, 3] → [1, 3, 6]).",
  "def kumulalt(xs: list[int]) -> list[int]", "import itertools\n\n\ndef kumulalt(xs):\n    return list(itertools.accumulate(xs))\n",
  ("xs: number[]): number[]", "let s = 0;\nreturn xs.map((x) => (s += x));"),
  [(([1, 2, 3],), [1, 3, 6]), (([],), [])], [(([5],), [5]), (([-1, 1, -1],), [-1, 0, -1]), (([0, 0],), [0, 0])])
h(0, "kozos", ["py.collections"], "intersect", "Közös elemek",
  "Írj `kozos(a: list[int], b: list[int]) -> list[int]` függvényt: az a azon elemei, amelyek b-ben is szerepelnek, az a-beli első előfordulás sorrendjében, ismétlődés nélkül.",
  "def kozos(a: list[int], b: list[int]) -> list[int]", "def kozos(a, b):\n    bs = set(b)\n    return [x for x in dict.fromkeys(a) if x in bs]\n",
  ("a: number[], b: number[]): number[]", "const bs = new Set(b);\nreturn [...new Set(a)].filter((x) => bs.has(x));"),
  [(([1, 2, 3, 2], [2, 3, 4]), [2, 3])], [(([], [1]), []), (([1, 1, 1], [1]), [1]), (([3, 2, 1], [1, 2, 3]), [3, 2, 1]), (([5], []), [])])
h(0, "binaris", ["py.basics", "py.errors"], "to-binary", "Kettes számrendszer",
  'Írj `binaris(n: int) -> str` függvényt, amely a nemnegatív n kettes számrendszerbeli alakját adja vissza vezető nullák nélkül (0 → "0"). Negatív n-re dobj `ValueError`-t.',
  "def binaris(n: int) -> str", "def binaris(n):\n    if n < 0:\n        raise ValueError(n)\n    return format(n, 'b')\n",
  ("n: number): string", "if (n < 0) throw new RangeError(String(n));\nreturn n.toString(2);"),
  [((5,), "101"), ((0,), "0")], [((1,), "1"), ((8,), "1000"), ((255,), "11111111"), ((1024,), "10000000000")], [(-1,)])
h(0, "atlagon_feluli", ["py.collections"], "above-mean", "Átlag fölötti elemek",
  "Írj `atlagon_feluli(xs: list[int]) -> list[int]` függvényt: a lista azon elemei, amelyek szigorúan nagyobbak a lista átlagánál, az eredeti sorrendben. Üres listára üres lista.",
  "def atlagon_feluli(xs: list[int]) -> list[int]", "def atlagon_feluli(xs):\n    return [x for x in xs if x * len(xs) > sum(xs)]\n",
  ("xs: number[]): number[]", "const s = xs.reduce((a, b) => a + b, 0);\nreturn xs.filter((x) => x * xs.length > s);"),
  [(([1, 2, 3, 4],), [3, 4]), (([],), [])], [(([5, 5, 5],), []), (([10, 0, 0],), [10]), (([-1, -2, 3],), [3]), (([1, 2],), [2])])
h(0, "csere", ["py.strings"], "swapcase", "Kis- és nagybetű csere",
  "Írj `csere(s: str) -> str` függvényt, amely minden kisbetűt nagybetűre, minden nagybetűt kisbetűre cserél; a többi karakter (számjegy, írásjel, szóköz) változatlan.",
  "def csere(s: str) -> str", "def csere(s):\n    return s.swapcase()\n",
  ("s: string): string", "return [...s].map((c) => (c === c.toUpperCase() ? c.toLowerCase() : c.toUpperCase())).join('');"),
  [(("AlMa",), "aLmA"), (("",), "")], [(("Árvíz 2024!",), "áRVÍZ 2024!"), (("ŐSZ",), "ősz"), (("x-Y",), "X-y")])
h(0, "terjedelem", ["py.collections"], "range", "Terjedelem",
  "Írj `terjedelem(xs: list[int]) -> int` függvényt: a legnagyobb és a legkisebb elem különbsége; üres listára 0.",
  "def terjedelem(xs: list[int]) -> int", "def terjedelem(xs):\n    return max(xs) - min(xs) if xs else 0\n",
  ("xs: number[]): number", "return xs.length ? Math.max(...xs) - Math.min(...xs) : 0;"),
  [(([3, 9, 1],), 8), (([],), 0)], [(([5],), 0), (([-5, 5],), 10), (([2, 2, 2],), 0), (([-10, -3],), 7)])
h(0, "van_ismetlodes", ["py.collections"], "has-dup", "Van-e ismétlődés",
  "Írj `van_ismetlodes(xs: list[int]) -> bool` függvényt: igaz, ha van olyan érték, amely legalább kétszer szerepel a listában.",
  "def van_ismetlodes(xs: list[int]) -> bool", "def van_ismetlodes(xs):\n    return len(set(xs)) < len(xs)\n",
  ("xs: number[]): boolean", "return new Set(xs).size < xs.length;"),
  [(([1, 2, 1],), True), (([1, 2, 3],), False)], [(([],), False), (([0, 0],), True), (([-1, 1],), False), (([5, 4, 3, 2, 1, 5],), True)])
h(0, "ido_formatum", ["py.strings", "py.errors"], "clock", "Időpont formázása",
  'Írj `ido_formatum(mp: int) -> str` függvényt: a nap 0 ≤ mp < 86400 másodpercét "ÓÓ:PP:MM" alakban adja vissza, kétjegyű, nullával kitöltött részekkel (pl. 3661 → "01:01:01"). Más értékre dobj `ValueError`-t.',
  "def ido_formatum(mp: int) -> str", code(r'''
    def ido_formatum(mp):
        if not 0 <= mp < 86400:
            raise ValueError(mp)
        return f'{mp // 3600:02d}:{mp // 60 % 60:02d}:{mp % 60:02d}'
  '''),
  ("mp: number): string", code(r'''
    if (!(mp >= 0 && mp < 86400)) throw new RangeError(String(mp));
    const p = (x: number) => String(x).padStart(2, '0');
    return `${p(Math.floor(mp / 3600))}:${p(Math.floor(mp / 60) % 60)}:${p(mp % 60)}`;
  ''')),
  [((3661,), "01:01:01"), ((0,), "00:00:00")], [((86399,), "23:59:59"), ((59,), "00:00:59"), ((43200,), "12:00:00")], [(-1,), (86400,)])

# ── L1 (42) ───────────────────────────────────────────────────────────────────
h(1, "caesar", ["py.strings"], "caesar", "Caesar-eltolás",
  "Írj `caesar(s: str, k: int) -> str` függvényt: az angol ábécé betűit (a–z, A–Z) k hellyel eltolja körbe, a kis- és nagybetűt megtartva; k lehet negatív vagy 26-nál nagyobb is. Minden más karakter (ékezetes betű, számjegy, szóköz, írásjel) változatlan.",
  "def caesar(s: str, k: int) -> str", code(r'''
    def caesar(s, k):
        out = []
        for c in s:
            if 'a' <= c <= 'z':
                out.append(chr((ord(c) - 97 + k) % 26 + 97))
            elif 'A' <= c <= 'Z':
                out.append(chr((ord(c) - 65 + k) % 26 + 65))
            else:
                out.append(c)
        return ''.join(out)
  '''),
  ("s: string, k: number): string", code(r'''
    const sh = (c: string, base: number) => String.fromCharCode(((((c.charCodeAt(0) - base + k) % 26) + 26) % 26) + base);
    return [...s].map((c) => (c >= 'a' && c <= 'z' ? sh(c, 97) : c >= 'A' && c <= 'Z' ? sh(c, 65) : c)).join('');
  ''')),
  [(("abc", 1), "bcd"), (("Zebra", 2), "Bgdtc")],
  [(("xyz", 3), "abc"), (("abc", -1), "zab"), (("Hello, World!", 27), "Ifmmp, Xpsme!"), (("árvíz", 1), "áswía"), (("abc", 0), "abc"), (("", 5), ""), (("ABC", -27), "ZAB")])
h(1, "szamrendszer", ["py.strings", "py.errors"], "base-out", "Átváltás b alapú számrendszerbe",
  'Írj `szamrendszer(n: int, b: int) -> str` függvényt: a nemnegatív n alakja b alapú számrendszerben (2 ≤ b ≤ 36), a 10–35 értékű jegyeket a–z kisbetűkkel jelölve, vezető nullák nélkül (0 → "0"). Negatív n-re vagy érvénytelen b-re dobj `ValueError`-t.',
  "def szamrendszer(n: int, b: int) -> str", code(r'''
    DIG = '0123456789abcdefghijklmnopqrstuvwxyz'


    def szamrendszer(n, b):
        if n < 0 or not 2 <= b <= 36:
            raise ValueError((n, b))
        out = ''
        while True:
            n, r = divmod(n, b)
            out = DIG[r] + out
            if n == 0:
                return out
  '''),
  ("n: number, b: number): string", "if (n < 0 || b < 2 || b > 36) throw new RangeError(`${n} ${b}`);\nreturn n.toString(b);"),
  [((255, 16), "ff"), ((0, 2), "0")], [((10, 2), "1010"), ((35, 36), "z"), ((36, 36), "10"), ((123456, 8), "361100"), ((7, 7), "10")],
  [(-1, 10), (5, 1), (5, 37)])
h(1, "szamrendszerbol", ["py.strings", "py.errors"], "base-in", "Beolvasás b alapú számrendszerből",
  "Írj `szamrendszerbol(s: str, b: int) -> int` függvényt: az s szöveget b alapú (2 ≤ b ≤ 36) nemnegatív számként értelmezi; a jegyek 0–9, majd a–z (kis- és nagybetű egyaránt), és mindegyik értéke kisebb b-nél. Üres szövegre, bármilyen más karakterre (előjel, szóköz, aláhúzás, előtag) vagy érvénytelen b-re dobj `ValueError`-t.",
  "def szamrendszerbol(s: str, b: int) -> int", code(r'''
    DIG = '0123456789abcdefghijklmnopqrstuvwxyz'


    def szamrendszerbol(s, b):
        if not 2 <= b <= 36 or not s:
            raise ValueError((s, b))
        n = 0
        for c in s.lower():
            d = DIG.find(c)
            if d < 0 or d >= b:
                raise ValueError(s)
            n = n * b + d
        return n
  '''),
  ("s: string, b: number): number", code(r'''
    const DIG = '0123456789abcdefghijklmnopqrstuvwxyz';
    if (b < 2 || b > 36 || s === '') throw new RangeError(s);
    let n = 0;
    for (const c of s.toLowerCase()) {
      const d = DIG.indexOf(c);
      if (d < 0 || d >= b) throw new RangeError(s);
      n = n * b + d;
    }
    return n;
  ''')),
  [(("ff", 16), 255), (("101", 2), 5)], [(("FF", 16), 255), (("z", 36), 35), (("0", 2), 0), (("777", 8), 511), (("10", 36), 36)],
  [("", 10), ("12", 2), ("-5", 10), ("1 0", 10), ("0x1f", 16), ("1_0", 10), ("5", 1), ("5", 37)])
h(1, "betu_gyakorisag", ["py.strings", "py.collections"], "letter-freq", "Betűgyakoriság",
  "Írj `betu_gyakorisag(s: str) -> dict[str, int]` függvényt: a szöveg betűit (`str.isalpha()`) kisbetűsítve megszámolja; a szótár kulcsai a kisbetűk, értékei a darabszámok. Más karakter nem számít.",
  "def betu_gyakorisag(s: str) -> dict[str, int]", code(r'''
    def betu_gyakorisag(s):
        d = {}
        for c in s.lower():
            if c.isalpha():
                d[c] = d.get(c, 0) + 1
        return d
  '''),
  ("s: string): Record<string, number>",
   "const d: Record<string, number> = {};\nfor (const c of s.toLowerCase()) if (/\\p{L}/u.test(c)) d[c] = (d[c] ?? 0) + 1;\nreturn d;"),
  [(("Alma",), {"a": 2, "l": 1, "m": 1}), (("",), {})], [(("Öt ökör!",), {"ö": 3, "t": 1, "k": 1, "r": 1}), (("123 ...",), {}), (("aA aA",), {"a": 4})])
h(1, "leghosszabb_novekvo", ["py.collections", "x.algo"], "run", "Leghosszabb növekvő szakasz",
  "Írj `leghosszabb_novekvo(xs: list[int]) -> int` függvényt: a lista leghosszabb szigorúan növekvő, összefüggő (szomszédos elemekből álló) szakaszának hossza; üres listára 0.",
  "def leghosszabb_novekvo(xs: list[int]) -> int", code(r'''
    def leghosszabb_novekvo(xs):
        best = cur = 0
        for i, x in enumerate(xs):
            cur = cur + 1 if i and x > xs[i - 1] else 1
            best = max(best, cur)
        return best
  '''),
  ("xs: number[]): number", code(r'''
    let best = 0;
    let cur = 0;
    xs.forEach((x, i) => {
      cur = i && x > xs[i - 1] ? cur + 1 : 1;
      best = Math.max(best, cur);
    });
    return best;
  ''')),
  [(([1, 2, 3, 1, 2],), 3), (([],), 0)], [(([5, 4, 3],), 1), (([1, 1, 1],), 1), (([1, 2, 2, 3, 4, 5],), 4), (([-3, -2, -1, 0],), 4), (([7],), 1)])
h(1, "ket_osszeg", ["py.collections", "x.algo"], "two-sum", "Két elem összege",
  "Írj `ket_osszeg(xs: list[int], cel: int) -> list[int] | None` függvényt: olyan [i, j] indexpárt ad vissza (i < j), amelyre xs[i] + xs[j] == cel; ha több ilyen van, a legkisebb j-vel, azon belül a legkisebb i-vel. Ha nincs ilyen pár, `None`.",
  "def ket_osszeg(xs: list[int], cel: int) -> list[int] | None", code(r'''
    def ket_osszeg(xs, cel):
        seen = {}
        for j, x in enumerate(xs):
            if cel - x in seen:
                return [seen[cel - x], j]
            seen.setdefault(x, j)
        return None
  '''),
  ("xs: number[], cel: number): number[] | null", code(r'''
    const seen = new Map<number, number>();
    for (let j = 0; j < xs.length; j++) {
      const i = seen.get(cel - xs[j]);
      if (i !== undefined) return [i, j];
      if (!seen.has(xs[j])) seen.set(xs[j], j);
    }
    return null;
  ''')),
  [(([2, 7, 11, 15], 9), [0, 1]), (([1, 2], 10), None)],
  [(([3, 3], 6), [0, 1]), (([1, 2, 3, 4], 7), [2, 3]), (([], 0), None), (([0, 4, 3, 0], 0), [0, 3]), (([5, 1, 5], 10), [0, 2]), (([-1, 3, 4], 2), [0, 1]), (([1, 5, 2, 4], 6), [0, 1])])
h(1, "mozgo_atlag", ["py.collections", "py.errors"], "moving-avg", "Mozgóátlag",
  "Írj `mozgo_atlag(xs: list[float], k: int) -> list[float]` függvényt: minden k hosszú, összefüggő ablak átlaga balról jobbra, két tizedesre kerekítve (`round(x, 2)`). Ha k nagyobb a lista hosszánál, üres lista; k < 1 esetén dobj `ValueError`-t.",
  "def mozgo_atlag(xs: list[float], k: int) -> list[float]", code(r'''
    def mozgo_atlag(xs, k):
        if k < 1:
            raise ValueError(k)
        return [round(sum(xs[i:i + k]) / k, 2) for i in range(len(xs) - k + 1)]
  '''),
  ("xs: number[], k: number): number[]", code(r'''
    if (k < 1) throw new RangeError(String(k));
    const out: number[] = [];
    for (let i = 0; i + k <= xs.length; i++) out.push(Math.round((xs.slice(i, i + k).reduce((a, b) => a + b, 0) / k) * 100) / 100);
    return out;
  ''')),
  [(([1, 2, 3, 4], 2), [1.5, 2.5, 3.5]), (([1, 2], 3), [])],
  [(([1, 2, 4], 3), [2.33]), (([1, 2, 5, 1], 3), [2.67, 2.67]), (([5], 1), [5]), (([2, 4, 6, 8, 10], 5), [6]), (([1, 1, 2], 2), [1, 1.5])],
  [([1], 0), ([], -1)])
h(1, "spiral", ["py.collections", "x.algo"], "spiral", "Csigavonal",
  "Írj `spiral(m: list[list[int]]) -> list[int]` függvényt: a téglalap alakú mátrix elemei csigavonalban, a bal felső saroktól indulva az óramutató járásával megegyezően (jobbra, le, balra, fel, majd befelé haladva). Üres mátrixra üres lista.",
  "def spiral(m: list[list[int]]) -> list[int]", code(r'''
    def spiral(m):
        out = []
        m = [list(r) for r in m]
        while m and m[0]:
            out += m.pop(0)
            if m and m[0]:
                for r in m:
                    out.append(r.pop())
            if m:
                out += m.pop()[::-1]
            if m and m[0]:
                for r in m[::-1]:
                    out.append(r.pop(0))
        return out
  '''),
  ("m: number[][]): number[]", code(r'''
    const out: number[] = [];
    let top = 0;
    let bot = m.length - 1;
    let left = 0;
    let right = (m[0]?.length ?? 0) - 1;
    while (top <= bot && left <= right) {
      for (let j = left; j <= right; j++) out.push(m[top][j]);
      top++;
      for (let i = top; i <= bot; i++) out.push(m[i][right]);
      right--;
      if (top <= bot) {
        for (let j = right; j >= left; j--) out.push(m[bot][j]);
        bot--;
      }
      if (left <= right) {
        for (let i = bot; i >= top; i--) out.push(m[i][left]);
        left++;
      }
    }
    return out;
  ''')),
  [(([[1, 2], [3, 4]],), [1, 2, 4, 3]), (([],), [])],
  [(([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), [1, 2, 3, 6, 9, 8, 7, 4, 5]), (([[1, 2], [3, 4], [5, 6]],), [1, 2, 4, 6, 5, 3]),
   (([[1], [2], [3]],), [1, 2, 3]), (([[1, 2, 3]],), [1, 2, 3]), (([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],), [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7])])
h(1, "matrix_szorzas", ["py.collections", "py.errors"], "matmul", "Mátrixszorzás",
  "Írj `matrix_szorzas(a: list[list[int]], b: list[list[int]]) -> list[list[int]]` függvényt: a két téglalap alakú mátrix a·b szorzata. Ha a oszlopainak száma nem egyezik b sorainak számával, vagy bármelyik mátrix üres, dobj `ValueError`-t.",
  "def matrix_szorzas(a: list[list[int]], b: list[list[int]]) -> list[list[int]]", code(r'''
    def matrix_szorzas(a, b):
        if not a or not b or len(a[0]) != len(b):
            raise ValueError('méret')
        return [[sum(x * y for x, y in zip(r, c, strict=True)) for c in zip(*b, strict=True)] for r in a]
  '''),
  ("a: number[][], b: number[][]): number[][]", code(r'''
    if (!a.length || !b.length || a[0].length !== b.length) throw new RangeError('méret');
    return a.map((r) => b[0].map((_, j) => r.reduce((s, x, k) => s + x * b[k][j], 0)));
  ''')),
  [(([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]])],
  [(([[1, 2, 3]], [[1], [2], [3]]), [[14]]), (([[2]], [[3]]), [[6]]), (([[1], [2]], [[3, 4]]), [[3, 4], [6, 8]]), (([[1, 0], [0, 1]], [[5, -1], [2, 7]]), [[5, -1], [2, 7]])],
  [([[1, 2]], [[1, 2]]), ([], [[1]]), ([[1]], [])])
h(1, "ipv4_ervenyes", ["py.strings"], "validate-ip", "IPv4-cím ellenőrzése",
  'Írj `ipv4_ervenyes(s: str) -> bool` függvényt: igaz, ha s pontosan négy, ponttal elválasztott részből áll; minden rész csak számjegyekből (0–9) áll, értéke 0–255, és nincs vezető nullája (a "0" maga megengedett). Minden más (szóköz, előjel, üres rész) hamis.',
  "def ipv4_ervenyes(s: str) -> bool", code(r'''
    def _resz(x):
        return x != '' and all('0' <= c <= '9' for c in x) and (x == '0' or x[0] != '0') and int(x) <= 255


    def ipv4_ervenyes(s):
        p = s.split('.')
        return len(p) == 4 and all(_resz(x) for x in p)
  '''),
  ("s: string): boolean", "const p = s.split('.');\nreturn p.length === 4 && p.every((x) => /^(0|[1-9][0-9]{0,2})$/.test(x) && Number(x) <= 255);"),
  [(("192.168.0.1",), True), (("256.1.1.1",), False)],
  [(("0.0.0.0",), True), (("255.255.255.255",), True), (("01.2.3.4",), False), (("1.2.3",), False), (("1.2.3.4.5",), False), (("1.2..4",), False),
   (("1.2.3.-4",), False), ((" 1.2.3.4",), False), (("1.2.3.4a",), False), (("1000.1.1.1",), False)])
h(1, "isbn10_ervenyes", ["py.strings", "x.algo"], "isbn", "ISBN-10 ellenőrzése",
  'Írj `isbn10_ervenyes(s: str) -> bool` függvényt. A kötőjeleket hagyd figyelmen kívül; ami marad, pontosan 10 karakter: az első 9 számjegy, az utolsó számjegy vagy nagy "X" (értéke 10). Érvényes, ha d1…d10 jegyekkel 10·d1 + 9·d2 + … + 1·d10 osztható 11-gyel. Minden más hamis.',
  "def isbn10_ervenyes(s: str) -> bool", code(r'''
    import re


    def isbn10_ervenyes(s):
        t = s.replace('-', '')
        if not re.fullmatch(r'[0-9]{9}[0-9X]', t):
            return False
        d = [10 if c == 'X' else int(c) for c in t]
        return sum((10 - i) * x for i, x in enumerate(d)) % 11 == 0
  '''),
  ("s: string): boolean", code(r'''
    const t = s.replace(/-/g, '');
    if (!/^[0-9]{9}[0-9X]$/.test(t)) return false;
    const d = [...t].map((c) => (c === 'X' ? 10 : Number(c)));
    return d.reduce((a, x, i) => a + (10 - i) * x, 0) % 11 === 0;
  ''')),
  [(("0-306-40615-2",), True), (("0-306-40615-3",), False)],
  [(("0306406152",), True), (("0-8044-2957-X",), True), (("0-8044-2957-x",), False), (("X-8044-2957-0",), False), (("030640615",), False),
   (("03064061522",), False), (("",), False), (("0 306 40615 2",), False)])
h(1, "luhn", ["py.strings", "x.algo"], "luhn", "Luhn-ellenőrzés",
  "Írj `luhn(s: str) -> bool` függvényt (Luhn-ellenőrzés): a szóközöket hagyd figyelmen kívül; ha ezután más, nem számjegy karakter is van benne, vagy 2-nél kevesebb számjegy marad, hamis. Jobbról a 2., 4., 6., … számjegyet duplázd, és ha a dupla 9-nél nagyobb, vonj le belőle 9-et; a szám érvényes, ha az így kapott jegyek összege osztható 10-zel.",
  "def luhn(s: str) -> bool", code(r'''
    def luhn(s):
        t = s.replace(' ', '')
        if len(t) < 2 or not all('0' <= c <= '9' for c in t):
            return False
        total = 0
        for i, c in enumerate(reversed(t)):
            d = int(c)
            if i % 2 == 1:
                d = d * 2 - 9 if d > 4 else d * 2
            total += d
        return total % 10 == 0
  '''),
  ("s: string): boolean", code(r'''
    const t = s.replace(/ /g, '');
    if (!/^[0-9]{2,}$/.test(t)) return false;
    let total = 0;
    [...t].reverse().forEach((c, i) => {
      let d = Number(c);
      if (i % 2 === 1) d = d > 4 ? d * 2 - 9 : d * 2;
      total += d;
    });
    return total % 10 === 0;
  ''')),
  [(("79927398713",), True), (("79927398710",), False)],
  [(("7992 7398 713",), True), (("059",), True), (("0",), False), ((" 0",), False), (("0000 0",), True), (("055-444",), False), (("59",), True), (("8a",), False)])
h(1, "intervallumok", ["py.collections", "x.algo", "py.errors"], "intervals", "Intervallumok összevonása",
  "Írj `intervallumok(iv: list[list[int]]) -> list[list[int]]` függvényt: a zárt [eleje, vége] intervallumokat (tetszőleges sorrendben) összevonja; az átfedő vagy érintkező (pl. [1, 2] és [2, 3]) intervallumokból egy lesz. Az eredmény eleje szerint növekvő. Ha valamelyiknél eleje > vége, dobj `ValueError`-t.",
  "def intervallumok(iv: list[list[int]]) -> list[list[int]]", code(r'''
    def intervallumok(iv):
        out = []
        for a, b in sorted(iv):
            if a > b:
                raise ValueError((a, b))
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out
  '''),
  ("iv: number[][]): number[][]", code(r'''
    const s = iv.map((p) => [...p]).sort((x, y) => x[0] - y[0] || x[1] - y[1]);
    const out: number[][] = [];
    for (const [a, b] of s) {
      if (a > b) throw new RangeError(`${a} ${b}`);
      const last = out[out.length - 1];
      if (last && a <= last[1]) last[1] = Math.max(last[1], b);
      else out.push([a, b]);
    }
    return out;
  ''')),
  [(([[1, 3], [2, 6], [8, 10]],), [[1, 6], [8, 10]]), (([],), [])],
  [(([[1, 2], [2, 3]],), [[1, 3]]), (([[5, 6], [1, 2]],), [[1, 2], [5, 6]]), (([[1, 10], [2, 3], [4, 5]],), [[1, 10]]), (([[3, 3]],), [[3, 3]]),
   (([[-5, -1], [-2, 0], [1, 1]],), [[-5, 0], [1, 1]])],
  [([[2, 1]],), ([[1, 2], [5, 4]],)])
h(1, "lnko_lista", ["x.algo", "py.errors"], "gcd", "Legnagyobb közös osztó",
  "Írj `lnko_lista(xs: list[int]) -> int` függvényt: a lista elemeinek legnagyobb közös osztója, nemnegatív szám (a negatív elemek abszolút értékével számolj; csupa 0 elemre 0). Üres listára dobj `ValueError`-t.",
  "def lnko_lista(xs: list[int]) -> int", "import math\n\n\ndef lnko_lista(xs):\n    if not xs:\n        raise ValueError('üres')\n    return math.gcd(*xs)\n",
  ("xs: number[]): number", code(r'''
    if (!xs.length) throw new RangeError('üres');
    const g = (a: number, b: number): number => (b === 0 ? a : g(b, a % b));
    return xs.reduce((a, x) => g(a, Math.abs(x)), 0);
  ''')),
  [(([12, 18],), 6), (([7],), 7)], [(([0, 0],), 0), (([-4, 6],), 2), (([17, 34, 51],), 17), (([9, 28],), 1), (([0, 5],), 5), (([-5],), 5)], [([],)])
h(1, "tokeletes", ["x.algo"], "perfect", "Tökéletes szám",
  "Írj `tokeletes(n: int) -> bool` függvényt: igaz, ha n pozitív egész, és egyenlő a nála kisebb pozitív osztóinak összegével (pl. 6 = 1 + 2 + 3). n ≤ 0 esetén hamis.",
  "def tokeletes(n: int) -> bool", code(r'''
    def tokeletes(n):
        if n < 2:
            return False
        s, i = 1, 2
        while i * i <= n:
            if n % i == 0:
                s += i if i * i == n else i + n // i
            i += 1
        return s == n
  '''),
  ("n: number): boolean", code(r'''
    if (n < 2) return false;
    let s = 1;
    for (let i = 2; i * i <= n; i++) if (n % i === 0) s += i * i === n ? i : i + n / i;
    return s === n;
  ''')),
  [((6,), True), ((8,), False)], [((28,), True), ((496,), True), ((8128,), True), ((1,), False), ((0,), False), ((-6,), False), ((12,), False), ((33550336,), True)])
h(1, "collatz_lepesek", ["x.algo", "py.errors"], "collatz", "Collatz-lépések",
  "Írj `collatz_lepesek(n: int) -> int` függvényt: hány lépésben jut el n az 1-hez, ha páros n-ből n/2, páratlanból 3n + 1 lesz (1 → 0 lépés). n < 1 esetén dobj `ValueError`-t.",
  "def collatz_lepesek(n: int) -> int", code(r'''
    def collatz_lepesek(n):
        if n < 1:
            raise ValueError(n)
        k = 0
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            k += 1
        return k
  '''),
  ("n: number): number", code(r'''
    if (n < 1) throw new RangeError(String(n));
    let k = 0;
    while (n !== 1) {
      n = n % 2 === 0 ? n / 2 : 3 * n + 1;
      k++;
    }
    return k;
  ''')),
  [((6,), 8), ((1,), 0)], [((2,), 1), ((7,), 16), ((27,), 111), ((12,), 9)], [(0,), (-3,)])
h(1, "kozos_elotag", ["py.strings"], "prefix", "Közös előtag",
  "Írj `kozos_elotag(szavak: list[str]) -> str` függvényt: a szavak leghosszabb közös előtagja (a kis- és nagybetű különbözik). Üres listára üres szöveg.",
  "def kozos_elotag(szavak: list[str]) -> str", code(r'''
    def kozos_elotag(szavak):
        if not szavak:
            return ''
        p = szavak[0]
        for w in szavak[1:]:
            while not w.startswith(p):
                p = p[:-1]
        return p
  '''),
  ("szavak: string[]): string", "if (!szavak.length) return '';\nlet p = szavak[0];\nfor (const w of szavak.slice(1)) while (!w.startsWith(p)) p = p.slice(0, -1);\nreturn p;"),
  [((["virág", "virágzik", "virgonc"],), "vir"), (([],), "")],
  [((["alma"],), "alma"), ((["Alma", "alma"],), ""), ((["", "a"],), ""), ((["ház", "ház"],), "ház"), ((["előtag", "előre", "elő"],), "elő")])
h(1, "pangramma", ["py.strings"], "pangram", "Pangramma",
  "Írj `pangramma(s: str) -> bool` függvényt: igaz, ha a szövegben az angol ábécé mind a 26 betűje (a–z) előfordul legalább egyszer, kis- és nagybetűtől függetlenül. A többi karakter nem számít.",
  "def pangramma(s: str) -> bool", "def pangramma(s):\n    return set('abcdefghijklmnopqrstuvwxyz') <= set(s.lower())\n",
  ("s: string): boolean", "const t = s.toLowerCase();\nreturn [...'abcdefghijklmnopqrstuvwxyz'].every((c) => t.includes(c));"),
  [(("The quick brown fox jumps over the lazy dog",), True), (("abc",), False)],
  [(("",), False), (("ABCDEFGHIJKLMNOPQRSTUVWXYZ",), True), (("abcdefghijklmnopqrstuvwxy",), False), (("Pack my box with five dozen liquor jugs.",), True),
   (("árvíztűrő tükörfúrógép",), False)])
h(1, "min_ermek", ["x.algo", "py.errors"], "coin-change", "Legkevesebb érme",
  "Írj `min_ermek(osszeg: int, cimletek: list[int]) -> int` függvényt: legalább hány érme kell az osszeg pontos kifizetéséhez, ha minden (pozitív) címletből korlátlanul van. Ha nem lehet kifizetni, -1; osszeg = 0 esetén 0. Negatív osszeg esetén dobj `ValueError`-t. Vigyázz: a mohó stratégia nem mindig optimális.",
  "def min_ermek(osszeg: int, cimletek: list[int]) -> int", code(r'''
    def min_ermek(osszeg, cimletek):
        if osszeg < 0:
            raise ValueError(osszeg)
        inf = osszeg + 1
        best = [inf] * (osszeg + 1)
        best[0] = 0
        for v in range(1, osszeg + 1):
            for c in cimletek:
                if c <= v and best[v - c] + 1 < best[v]:
                    best[v] = best[v - c] + 1
        return best[osszeg] if best[osszeg] < inf else -1
  '''),
  ("osszeg: number, cimletek: number[]): number", code(r'''
    if (osszeg < 0) throw new RangeError(String(osszeg));
    const best = [0, ...Array(osszeg).fill(Infinity)];
    for (let v = 1; v <= osszeg; v++) for (const c of cimletek) if (c <= v && best[v - c] + 1 < best[v]) best[v] = best[v - c] + 1;
    return Number.isFinite(best[osszeg]) ? best[osszeg] : -1;
  ''')),
  [((11, [1, 2, 5]), 3), ((3, [2]), -1)],
  [((0, [1]), 0), ((6, [1, 3, 4]), 2), ((7, [2, 4]), -1), ((100, [1, 5, 10, 25, 50]), 2), ((63, [1, 5, 10, 21, 25]), 3), ((1, []), -1)],
  [(-1, [1])])
h(1, "lepcso", ["x.algo", "py.errors"], "stairs", "Lépcsőn felfelé",
  "Írj `lepcso(n: int) -> int` függvényt: hányféleképpen lehet felmenni egy n fokú lépcsőn, ha egyszerre 1 vagy 2 fokot lépünk (n = 0 esetén 1). Negatív n-re dobj `ValueError`-t. n legfeljebb 70.",
  "def lepcso(n: int) -> int", code(r'''
    def lepcso(n):
        if n < 0:
            raise ValueError(n)
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return a
  '''),
  ("n: number): number", "if (n < 0) throw new RangeError(String(n));\nlet a = 1;\nlet b = 1;\nfor (let i = 0; i < n; i++) [a, b] = [b, a + b];\nreturn a;"),
  [((3,), 3), ((0,), 1)], [((1,), 1), ((2,), 2), ((10,), 89), ((70,), 308061521170129)], [(-1,)])
h(1, "permutaciok", ["py.strings", "x.algo"], "permutations", "Permutációk",
  'Írj `permutaciok(s: str) -> list[str]` függvényt: s karaktereinek összes KÜLÖNBÖZŐ sorrendje, karakterkód szerint növekvő rendezésben. Üres szövegre [""].',
  "def permutaciok(s: str) -> list[str]", "import itertools\n\n\ndef permutaciok(s):\n    return sorted({''.join(p) for p in itertools.permutations(s)})\n",
  ("s: string): string[]", code(r'''
    const out = new Set<string>();
    const go = (rest: string, acc: string): void => {
      if (!rest) {
        out.add(acc);
        return;
      }
      for (let i = 0; i < rest.length; i++) go(rest.slice(0, i) + rest.slice(i + 1), acc + rest[i]);
    };
    go(s, '');
    return [...out].sort();
  ''')),
  [(("ab",), ["ab", "ba"]), (("",), [""])],
  [(("aab",), ["aab", "aba", "baa"]), (("abc",), ["abc", "acb", "bac", "bca", "cab", "cba"]), (("x",), ["x"]), (("Ba",), ["Ba", "aB"]), (("aaa",), ["aaa"])])
h(1, "kombinacio", ["x.algo", "py.errors"], "binomial", "Kombinációk száma",
  "Írj `kombinacio(n: int, k: int) -> int` függvényt: n elemből k elem kiválasztásainak száma (binomiális együttható). Ha k < 0 vagy k > n, 0. Negatív n-re dobj `ValueError`-t. Az eredmény kisebb 2^53-nál.",
  "def kombinacio(n: int, k: int) -> int", "import math\n\n\ndef kombinacio(n, k):\n    if n < 0:\n        raise ValueError(n)\n    return math.comb(n, k) if 0 <= k <= n else 0\n",
  ("n: number, k: number): number", code(r'''
    if (n < 0) throw new RangeError(String(n));
    if (k < 0 || k > n) return 0;
    k = Math.min(k, n - k);
    let r = 1;
    for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
    return r;
  ''')),
  [((5, 2), 10), ((3, 5), 0)], [((0, 0), 1), ((10, 0), 1), ((10, 10), 1), ((4, -1), 0), ((20, 10), 184756), ((50, 25), 126410606437752)], [(-1, 0)])
h(1, "szam_betuvel", ["py.strings", "py.errors"], "number-words", "Szám betűvel",
  "Írj `szam_betuvel(n: int) -> str` függvényt, amely a 0 ≤ n ≤ 99 számot magyarul, betűvel, egybeírva adja vissza. Egyesek: nulla, egy, kettő, három, négy, öt, hat, hét, nyolc, kilenc; kerek tízesek: tíz, húsz, harminc, negyven, ötven, hatvan, hetven, nyolcvan, kilencven. A 11–19 alakja tizen + egyes (tizenegy), a 21–29-é huszon + egyes (huszonkettő), a többi tízes + egyes (harmincöt). A nulla csak önmagában szerepel. Más n-re dobj `ValueError`-t.",
  "def szam_betuvel(n: int) -> str", code(r'''
    EGY = ['', 'egy', 'kettő', 'három', 'négy', 'öt', 'hat', 'hét', 'nyolc', 'kilenc']
    TIZ = ['', 'tíz', 'húsz', 'harminc', 'negyven', 'ötven', 'hatvan', 'hetven', 'nyolcvan', 'kilencven']
    KOT = ['', 'tizen', 'huszon', *TIZ[3:]]


    def szam_betuvel(n):
        if not 0 <= n <= 99:
            raise ValueError(n)
        if n == 0:
            return 'nulla'
        t, e = divmod(n, 10)
        return TIZ[t] if e == 0 else KOT[t] + EGY[e]
  '''),
  ("n: number): string", code(r'''
    if (!(n >= 0 && n <= 99)) throw new RangeError(String(n));
    if (n === 0) return 'nulla';
    const EGY = ['', 'egy', 'kettő', 'három', 'négy', 'öt', 'hat', 'hét', 'nyolc', 'kilenc'];
    const TIZ = ['', 'tíz', 'húsz', 'harminc', 'negyven', 'ötven', 'hatvan', 'hetven', 'nyolcvan', 'kilencven'];
    const KOT = ['', 'tizen', 'huszon', ...TIZ.slice(3)];
    const t = Math.floor(n / 10);
    const e = n % 10;
    return e === 0 ? TIZ[t] : KOT[t] + EGY[e];
  ''')),
  [((7,), "hét"), ((21,), "huszonegy")],
  [((0,), "nulla"), ((10,), "tíz"), ((11,), "tizenegy"), ((12,), "tizenkettő"), ((20,), "húsz"), ((35,), "harmincöt"), ((99,), "kilencvenkilenc"),
   ((40,), "negyven"), ((2,), "kettő")],
  [(-1,), (100,)])
h(1, "honap_napjai", ["py.basics", "py.errors"], "month-days", "A hónap napjai",
  "Írj `honap_napjai(ev: int, ho: int) -> int` függvényt: hány napos az adott év ho. hónapja (1 = január) a Gergely-naptárban; a február szökőévben 29 napos (szökőév: 4-gyel osztható, kivéve a 100-zal oszthatókat, de a 400-zal oszthatók igen). Ha ho nem 1 és 12 közötti, dobj `ValueError`-t.",
  "def honap_napjai(ev: int, ho: int) -> int", code(r'''
    def honap_napjai(ev, ho):
        if not 1 <= ho <= 12:
            raise ValueError(ho)
        if ho == 2:
            return 29 if ev % 4 == 0 and (ev % 100 != 0 or ev % 400 == 0) else 28
        return 30 if ho in (4, 6, 9, 11) else 31
  '''),
  ("ev: number, ho: number): number", code(r'''
    if (!(ho >= 1 && ho <= 12)) throw new RangeError(String(ho));
    if (ho === 2) return ev % 4 === 0 && (ev % 100 !== 0 || ev % 400 === 0) ? 29 : 28;
    return [4, 6, 9, 11].includes(ho) ? 30 : 31;
  ''')),
  [((2024, 2), 29), ((2023, 1), 31)], [((2023, 2), 28), ((1900, 2), 28), ((2000, 2), 29), ((2023, 4), 30), ((2023, 12), 31), ((2023, 11), 30), ((2023, 7), 31)],
  [(2023, 0), (2023, 13)])
h(1, "het_napja", ["py.basics", "py.errors"], "weekday", "A hét napja",
  "Írj `het_napja(ev: int, ho: int, nap: int) -> str` függvényt, amely a (visszafelé is kiterjesztett) Gergely-naptár szerinti dátum napjának magyar nevét adja vissza kisbetűvel: hétfő, kedd, szerda, csütörtök, péntek, szombat, vasárnap. Az ev 1 és 9999 közötti. Nem létező dátumra (pl. február 30.) dobj `ValueError`-t.",
  "def het_napja(ev: int, ho: int, nap: int) -> str", code(r'''
    import datetime

    NEVEK = ['hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat', 'vasárnap']


    def het_napja(ev, ho, nap):
        return NEVEK[datetime.date(ev, ho, nap).weekday()]
  '''),
  ("ev: number, ho: number, nap: number): string", code(r'''
    const d = new Date(0);
    d.setUTCFullYear(ev, ho - 1, nap);
    if (d.getUTCFullYear() !== ev || d.getUTCMonth() !== ho - 1 || d.getUTCDate() !== nap) throw new RangeError(`${ev}-${ho}-${nap}`);
    return ['vasárnap', 'hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat'][d.getUTCDay()];
  ''')),
  [((2024, 1, 1), "hétfő"), ((2000, 1, 1), "szombat")],
  [((1970, 1, 1), "csütörtök"), ((2024, 2, 29), "csütörtök"), ((1848, 3, 15), "szerda"), ((1, 1, 1), "hétfő"), ((9999, 12, 31), "péntek")],
  [(2023, 2, 29), (2024, 2, 30), (2024, 13, 1), (2024, 4, 31), (2024, 1, 0)])
h(1, "csv_sor", ["py.strings", "py.errors"], "csv", "CSV-sor felbontása",
  'Írj `csv_sor(s: str) -> list[str]` függvényt, amely egy CSV-sort mezőkre bont. A mezőket vessző választja el. Ha egy mező idézőjellel (") kezdődik, a záró idézőjelig tart: benne a vessző sima karakter, a "" pedig egyetlen " karaktert jelent; a záró idézőjel után csak vessző vagy a sor vége jöhet. Idézőjellel nem kezdődő mezőben nem lehet idézőjel. Üres szövegre [""]. Szabálytalan sorra (le nem zárt idézőjel, idézőjel rossz helyen) dobj `ValueError`-t.',
  "def csv_sor(s: str) -> list[str]", code(r'''
    def csv_sor(s):
        out, i, n = [], 0, len(s)
        while True:
            if i < n and s[i] == '"':
                i += 1
                buf = []
                while True:
                    if i >= n:
                        raise ValueError('lezáratlan idézőjel')
                    if s[i] == '"':
                        if i + 1 < n and s[i + 1] == '"':
                            buf.append('"')
                            i += 2
                            continue
                        i += 1
                        break
                    buf.append(s[i])
                    i += 1
                if i < n and s[i] != ',':
                    raise ValueError('szöveg a záró idézőjel után')
                out.append(''.join(buf))
            else:
                j = s.find(',', i)
                j = n if j < 0 else j
                if '"' in s[i:j]:
                    raise ValueError('idézőjel a mezőben')
                out.append(s[i:j])
                i = j
            if i >= n:
                return out
            i += 1
  '''),
  ("s: string): string[]", code(r'''
    const out: string[] = [];
    const n = s.length;
    let i = 0;
    for (;;) {
      if (s[i] === '"') {
        i++;
        let buf = '';
        for (;;) {
          if (i >= n) throw new RangeError('lezáratlan idézőjel');
          if (s[i] === '"') {
            if (s[i + 1] === '"') {
              buf += '"';
              i += 2;
              continue;
            }
            i++;
            break;
          }
          buf += s[i++];
        }
        if (i < n && s[i] !== ',') throw new RangeError('szöveg a záró idézőjel után');
        out.push(buf);
      } else {
        let j = s.indexOf(',', i);
        if (j < 0) j = n;
        const mezo = s.slice(i, j);
        if (mezo.includes('"')) throw new RangeError('idézőjel a mezőben');
        out.push(mezo);
        i = j;
      }
      if (i >= n) return out;
      i++;
    }
  ''')),
  [(("a,b,c",), ["a", "b", "c"]), (('"x,y",z',), ["x,y", "z"])],
  [(("",), [""]), (("a,",), ["a", ""]), ((",",), ["", ""]), (('"mondd: ""szia""",2',), ['mondd: "szia"', "2"]), (('"",x',), ["", "x"]),
   (("egy, kettő",), ["egy", " kettő"]), (('"a"',), ["a"])],
  [('"abc',), ('"a"b,c',), ('a"b',), ('"a""',)])
h(1, "ezres_tagolas", ["py.strings"], "thousands", "Ezres tagolás",
  'Írj `ezres_tagolas(n: int) -> str` függvényt: az egész szám számjegyeit jobbról hármas csoportokra tagolja, a csoportok közé egy szóközt téve (pl. 1234567 → "1 234 567"); negatív számnál a mínuszjel elöl marad ("-1 234").',
  "def ezres_tagolas(n: int) -> str", "def ezres_tagolas(n):\n    return format(n, ',').replace(',', ' ')\n",
  ("n: number): string", "const d = String(Math.abs(n)).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ' ');\nreturn n < 0 ? '-' + d : d;"),
  [((1234567,), "1 234 567"), ((0,), "0")],
  [((999,), "999"), ((1000,), "1 000"), ((-1234,), "-1 234"), ((-5,), "-5"), ((100000,), "100 000"), ((12345678901,), "12 345 678 901")])
h(1, "racs_ut", ["x.algo", "x.ds"], "grid-bfs", "Legrövidebb út a rácson",
  "Írj `racs_ut(racs: list[str]) -> int` függvényt. A rács sorai egyforma hosszú szövegek: '.' szabad mező, '#' fal. Legkevesebb hány lépésben jutunk el a bal felső sarokból a jobb alsóba, ha mindig egy vízszintesen vagy függőlegesen szomszédos szabad mezőre lépünk? Ha nem lehet (vagy a kezdő, illetve a cél mező fal, vagy a rács üres), -1; ha a kezdő mező egyben a cél, 0.",
  "def racs_ut(racs: list[str]) -> int", code(r'''
    from collections import deque


    def racs_ut(racs):
        if not racs or not racs[0]:
            return -1
        h, w = len(racs), len(racs[0])
        if racs[0][0] == '#' or racs[h - 1][w - 1] == '#':
            return -1
        dist = {(0, 0): 0}
        q = deque([(0, 0)])
        while q:
            r, c = q.popleft()
            if (r, c) == (h - 1, w - 1):
                return dist[(r, c)]
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < h and 0 <= nc < w and racs[nr][nc] == '.' and (nr, nc) not in dist:
                    dist[(nr, nc)] = dist[(r, c)] + 1
                    q.append((nr, nc))
        return -1
  '''),
  ("racs: string[]): number", code(r'''
    if (!racs.length || !racs[0].length) return -1;
    const h = racs.length;
    const w = racs[0].length;
    if (racs[0][0] === '#' || racs[h - 1][w - 1] === '#') return -1;
    const dist = new Map<number, number>([[0, 0]]);
    const q = [0];
    for (let qi = 0; qi < q.length; qi++) {
      const r = Math.floor(q[qi] / w);
      const c = q[qi] % w;
      const d = dist.get(q[qi])!;
      if (r === h - 1 && c === w - 1) return d;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        const k = nr * w + nc;
        if (nr >= 0 && nr < h && nc >= 0 && nc < w && racs[nr][nc] === '.' && !dist.has(k)) {
          dist.set(k, d + 1);
          q.push(k);
        }
      }
    }
    return -1;
  ''')),
  [((["..", ".."],), 2), ((["#."],), -1)],
  [((["."],), 0), (([".#.", ".#.", "..."],), 4), (([".#", "#."],), -1), (([],), -1), (([".#"],), -1), ((["....."],), 4),
   ((["...", "##.", "...", ".##", "..."],), 10)])
h(1, "szigetek", ["x.algo", "x.ds"], "islands", "Szigetek száma",
  "Írj `szigetek(terkep: list[str]) -> int` függvényt. A térkép egyforma hosszú sorokból áll: '#' szárazföld, '.' víz. Hány sziget van, ha a vízszintesen vagy függőlegesen szomszédos szárazföld-mezők ugyanahhoz a szigethez tartoznak (az átlósak nem)?",
  "def szigetek(terkep: list[str]) -> int", code(r'''
    def szigetek(terkep):
        h = len(terkep)
        w = len(terkep[0]) if h else 0
        seen = set()
        db = 0
        for r in range(h):
            for c in range(w):
                if terkep[r][c] != '#' or (r, c) in seen:
                    continue
                db += 1
                seen.add((r, c))
                stack = [(r, c)]
                while stack:
                    y, x = stack.pop()
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < h and 0 <= nx < w and terkep[ny][nx] == '#' and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
        return db
  '''),
  ("terkep: string[]): number", code(r'''
    const h = terkep.length;
    const w = h ? terkep[0].length : 0;
    const seen = new Set<number>();
    let db = 0;
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        if (terkep[r][c] !== '#' || seen.has(r * w + c)) continue;
        db++;
        seen.add(r * w + c);
        const stack = [[r, c]];
        while (stack.length) {
          const [y, x] = stack.pop()!;
          for (const [ny, nx] of [[y + 1, x], [y - 1, x], [y, x + 1], [y, x - 1]]) {
            if (ny >= 0 && ny < h && nx >= 0 && nx < w && terkep[ny][nx] === '#' && !seen.has(ny * w + nx)) {
              seen.add(ny * w + nx);
              stack.push([ny, nx]);
            }
          }
        }
      }
    }
    return db;
  ''')),
  [((["#..", "..#"],), 2), (([],), 0)],
  [((["#.#", ".#.", "#.#"],), 5), ((["###", "#.#", "###"],), 1), ((["...", "..."],), 0), ((["#"],), 1), ((["##..", "#..#", "..##", "#..."],), 3)])
h(1, "rpn", ["x.ds", "py.errors"], "rpn", "Fordított lengyel jelölés",
  'Írj `rpn(kif: str) -> int` függvényt, amely egy fordított lengyel jelölésű kifejezést értékel ki. A tokeneket egy vagy több szóköz választja el; egy token vagy egész szám (lehet negatív, pl. "-3"), vagy a +, -, * műveleti jelek egyike. Szabálytalan kifejezésre (ismeretlen token, kevés operandus, a végén nem pontosan egy érték marad, üres kifejezés) dobj `ValueError`-t.',
  "def rpn(kif: str) -> int", code(r'''
    import re


    def rpn(kif):
        st = []
        for t in kif.split():
            if re.fullmatch(r'-?[0-9]+', t):
                st.append(int(t))
            elif t in ('+', '-', '*'):
                if len(st) < 2:
                    raise ValueError('kevés operandus')
                b, a = st.pop(), st.pop()
                st.append(a + b if t == '+' else a - b if t == '-' else a * b)
            else:
                raise ValueError(t)
        if len(st) != 1:
            raise ValueError('nem egy érték maradt')
        return st[0]
  '''),
  ("kif: string): number", code(r'''
    const st: number[] = [];
    for (const t of kif.split(' ').filter(Boolean)) {
      if (/^-?[0-9]+$/.test(t)) st.push(Number(t));
      else if (t === '+' || t === '-' || t === '*') {
        if (st.length < 2) throw new RangeError('kevés operandus');
        const b = st.pop()!;
        const a = st.pop()!;
        st.push(t === '+' ? a + b : t === '-' ? a - b : a * b);
      } else throw new RangeError(t);
    }
    if (st.length !== 1) throw new RangeError('nem egy érték maradt');
    return st[0];
  ''')),
  [(("3 4 +",), 7), (("5 1 2 + 4 * + 3 -",), 14)],
  [(("42",), 42), (("-3 2 *",), -6), (("2 3 -",), -1), (("  1   2 +  ",), 3), (("1 2 3 * +",), 7)],
  [("",), ("1 +",), ("1 2",), ("1 2 /",), ("a",), ("+",)])
h(1, "matrix_forgat", ["py.collections", "py.errors"], "rotate-matrix", "Mátrix forgatása",
  "Írj `matrix_forgat(m: list[list[int]]) -> list[list[int]]` függvényt: a mátrixot 90 fokkal az óramutató járásával megegyezően elforgatva adja vissza. Üres mátrixra üres lista. Ha a sorok nem egyforma hosszúak, dobj `ValueError`-t.",
  "def matrix_forgat(m: list[list[int]]) -> list[list[int]]", code(r'''
    def matrix_forgat(m):
        if any(len(r) != len(m[0]) for r in m):
            raise ValueError('nem téglalap')
        return [list(r) for r in zip(*m[::-1], strict=True)]
  '''),
  ("m: number[][]): number[][]", code(r'''
    if (m.some((r) => r.length !== m[0].length)) throw new RangeError('nem téglalap');
    return m.length ? m[0].map((_, j) => m.map((r) => r[j]).reverse()) : [];
  ''')),
  [(([[1, 2], [3, 4]],), [[3, 1], [4, 2]]), (([],), [])],
  [(([[1, 2, 3]],), [[1], [2], [3]]), (([[1], [2], [3]],), [[3, 2, 1]]), (([[1, 2, 3], [4, 5, 6]],), [[4, 1], [5, 2], [6, 3]]), (([[7]],), [[7]])],
  [([[1, 2], [3]],)])
h(1, "csucsok", ["py.collections"], "peaks", "Csúcsok",
  "Írj `csucsok(xs: list[int]) -> list[int]` függvényt: azon i indexek növekvő sorrendben, ahol xs[i] szigorúan nagyobb minden létező szomszédjánál (az első és az utolsó elemnek csak egy szomszédja van, egyelemű listában az egyetlen elem csúcs). Üres listára üres lista.",
  "def csucsok(xs: list[int]) -> list[int]", code(r'''
    def csucsok(xs):
        n = len(xs)
        return [i for i in range(n) if (i == 0 or xs[i] > xs[i - 1]) and (i == n - 1 or xs[i] > xs[i + 1])]
  '''),
  ("xs: number[]): number[]", "return xs.flatMap((x, i) => ((i === 0 || x > xs[i - 1]) && (i === xs.length - 1 || x > xs[i + 1]) ? [i] : []));"),
  [(([1, 3, 2],), [1]), (([],), [])],
  [(([5],), [0]), (([3, 1, 2],), [0, 2]), (([1, 1, 1],), []), (([1, 2, 3, 4],), [3]), (([2, 1, 3, 1, 4],), [0, 2, 4]), (([1, 2, 2, 1],), [])])
h(1, "elso_egyedi", ["py.strings", "py.collections"], "first-unique", "Első egyedi karakter",
  "Írj `elso_egyedi(s: str) -> str | None` függvényt: a szöveg első olyan karaktere, amely pontosan egyszer fordul elő benne (a kis- és nagybetű különbözik); ha nincs ilyen, `None`.",
  "def elso_egyedi(s: str) -> str | None", code(r'''
    from collections import Counter


    def elso_egyedi(s):
        c = Counter(s)
        return next((ch for ch in s if c[ch] == 1), None)
  '''),
  ("s: string): string | null", code(r'''
    const c = new Map<string, number>();
    for (const ch of s) c.set(ch, (c.get(ch) ?? 0) + 1);
    for (const ch of s) if (c.get(ch) === 1) return ch;
    return null;
  ''')),
  [(("alma",), "l"), (("aabb",), None)], [(("",), None), (("x",), "x"), (("aA",), "a"), (("kakukk",), "a"), (("abcabcd",), "d"), (("őrölő",), "r")])
h(1, "hamming", ["py.strings", "py.errors"], "hamming", "Hamming-távolság",
  "Írj `hamming(a: str, b: str) -> int` függvényt: hány pozícióban különbözik a két egyforma hosszú szöveg. Ha a hosszuk eltér, dobj `ValueError`-t.",
  "def hamming(a: str, b: str) -> int", code(r'''
    def hamming(a, b):
        if len(a) != len(b):
            raise ValueError('eltérő hossz')
        return sum(x != y for x, y in zip(a, b, strict=True))
  '''),
  ("a: string, b: string): number", "if (a.length !== b.length) throw new RangeError('eltérő hossz');\nreturn [...a].filter((c, i) => c !== b[i]).length;"),
  [(("GAGCCT", "CATCGT"), 3), (("", ""), 0)], [(("abc", "abc"), 0), (("abc", "abd"), 1), (("ő", "o"), 1), (("Alma", "alma"), 1)], [("a", ""), ("ab", "abc")])
h(1, "levenshtein", ["py.strings", "x.algo"], "edit-distance", "Szerkesztési távolság",
  "Írj `levenshtein(a: str, b: str) -> int` függvényt: a két szöveg szerkesztési távolsága, vagyis legkevesebb hány egykarakteres beszúrás, törlés vagy csere kell ahhoz, hogy a-ból b legyen.",
  "def levenshtein(a: str, b: str) -> int", code(r'''
    def levenshtein(a, b):
        prev = list(range(len(b) + 1))
        for i, x in enumerate(a, 1):
            cur = [i]
            for j, y in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
            prev = cur
        return prev[-1]
  '''),
  ("a: string, b: string): number", code(r'''
    let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)));
      prev = cur;
    }
    return prev[b.length];
  ''')),
  [(("kitten", "sitting"), 3), (("", ""), 0)],
  [(("", "abc"), 3), (("abc", ""), 3), (("alma", "alma"), 0), (("flaw", "lawn"), 2), (("ház", "háziasszony"), 8), (("körte", "körtefa"), 2)])
h(1, "szo_minta", ["py.strings", "py.collections"], "word-pattern", "Szóminta",
  "Írj `szo_minta(minta: str, s: str) -> bool` függvényt: igaz, ha s `str.split()` szerinti szavai pontosan annyian vannak, ahány karakteres a minta, és a minta karakterei és a szavak között kölcsönösen egyértelmű a megfeleltetés (azonos karakter ↔ azonos szó, különböző karakter ↔ különböző szó).",
  "def szo_minta(minta: str, s: str) -> bool", code(r'''
    def szo_minta(minta, s):
        w = s.split()
        if len(w) != len(minta):
            return False
        return len(set(minta)) == len(set(w)) == len(set(zip(minta, w, strict=True)))
  '''),
  ("minta: string, s: string): boolean", code(r'''
    const w = s.split(/\s+/).filter(Boolean);
    const p = [...minta];
    if (w.length !== p.length) return false;
    const pairs = new Set(p.map((c, i) => c + '\u0000' + w[i]));
    return new Set(p).size === new Set(w).size && pairs.size === new Set(w).size;
  ''')),
  [(("abba", "kutya macska macska kutya"), True), (("abba", "kutya macska macska hal"), False)],
  [(("aaaa", "kutya kutya kutya kutya"), True), (("abba", "kutya kutya kutya kutya"), False), (("ab", "kutya"), False), (("", ""), True),
   (("ab", "x x"), False), (("ab", "x y"), True), (("aab", "x x y"), True)])
h(1, "egyensuly_index", ["py.collections"], "pivot", "Egyensúlyi index",
  "Írj `egyensuly_index(xs: list[int]) -> int` függvényt: a legkisebb olyan i index, amelynél az előtte álló elemek összege egyenlő az utána állókéval (az i. elem egyikbe sem számít; az üres összeg 0). Ha nincs ilyen, -1.",
  "def egyensuly_index(xs: list[int]) -> int", code(r'''
    def egyensuly_index(xs):
        bal, ossz = 0, sum(xs)
        for i, x in enumerate(xs):
            if bal == ossz - bal - x:
                return i
            bal += x
        return -1
  '''),
  ("xs: number[]): number", code(r'''
    const ossz = xs.reduce((a, b) => a + b, 0);
    let bal = 0;
    for (let i = 0; i < xs.length; i++) {
      if (bal === ossz - bal - xs[i]) return i;
      bal += xs[i];
    }
    return -1;
  ''')),
  [(([1, 7, 3, 6, 5, 6],), 3), (([1, 2, 3],), -1)],
  [(([],), -1), (([5],), 0), (([2, 1, -1],), 0), (([0, 0, 0],), 0), (([1, -1, 4],), 2), (([-1, -1, -1, 0, 1, 1],), 0)])
h(1, "tobbi_szorzata", ["py.collections", "x.algo"], "product-except", "A többi elem szorzata",
  "Írj `tobbi_szorzata(xs: list[int]) -> list[int]` függvényt: az eredmény i. eleme az xs összes többi elemének szorzata (az i. kivételével; az üres szorzat 1). A lista nullát is tartalmazhat.",
  "def tobbi_szorzata(xs: list[int]) -> list[int]", code(r'''
    def tobbi_szorzata(xs):
        out = [1] * len(xs)
        p = 1
        for i, x in enumerate(xs):
            out[i] = p
            p *= x
        p = 1
        for i in range(len(xs) - 1, -1, -1):
            out[i] *= p
            p *= xs[i]
        return out
  '''),
  ("xs: number[]): number[]", code(r'''
    const out = xs.map(() => 1);
    let p = 1;
    for (let i = 0; i < xs.length; i++) {
      out[i] = p;
      p *= xs[i];
    }
    p = 1;
    for (let i = xs.length - 1; i >= 0; i--) {
      out[i] *= p;
      p *= xs[i];
    }
    return out;
  ''')),
  [(([1, 2, 3, 4],), [24, 12, 8, 6]), (([],), [])], [(([5],), [1]), (([2, 0, 3],), [0, 6, 0]), (([0, 0, 2],), [0, 0, 0]), (([-1, 2, -3],), [-6, 3, -2]), (([1, 1],), [1, 1])])
h(1, "huszar", ["py.strings", "py.errors"], "knight", "Huszárlépések",
  'Írj `huszar(mezo: str) -> list[str]` függvényt: a sakktábla adott mezőjéről (pl. "b1": oszlop a–h kisbetűvel, sor 1–8) a huszár által elérhető mezők ábécérendben. Érvénytelen mezőre dobj `ValueError`-t.',
  "def huszar(mezo: str) -> list[str]", code(r'''
    import re

    LEPES = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))


    def huszar(mezo):
        if not re.fullmatch(r'[a-h][1-8]', mezo):
            raise ValueError(mezo)
        c, r = ord(mezo[0]) - 97, int(mezo[1])
        return sorted(chr(97 + c + dc) + str(r + dr) for dc, dr in LEPES if 0 <= c + dc < 8 and 1 <= r + dr <= 8)
  '''),
  ("mezo: string): string[]", code(r'''
    if (!/^[a-h][1-8]$/.test(mezo)) throw new RangeError(mezo);
    const c = mezo.charCodeAt(0) - 97;
    const r = Number(mezo[1]);
    const out: string[] = [];
    for (const [dc, dr] of [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]) {
      if (c + dc >= 0 && c + dc < 8 && r + dr >= 1 && r + dr <= 8) out.push(String.fromCharCode(97 + c + dc) + (r + dr));
    }
    return out.sort();
  ''')),
  [(("b1",), ["a3", "c3", "d2"]), (("a1",), ["b3", "c2"])],
  [(("d4",), ["b3", "b5", "c2", "c6", "e2", "e6", "f3", "f5"]), (("h8",), ["f7", "g6"]), (("g1",), ["e2", "f3", "h3"])],
  [("i1",), ("a9",), ("A1",), ("",), ("a10",), ("a0",)])
h(1, "hex_szin", ["py.strings", "py.errors"], "hex-color", "Hexadecimális színkód",
  'Írj `hex_szin(s: str) -> list[int]` függvényt: a "#rrggbb" vagy a rövid "#rgb" alakú színkódot [r, g, b] egészekre (0–255) bontja. A hexadecimális jegyek kis- és nagybetűsek is lehetnek; a rövid alakban minden jegy megduplázódik ("#f80" = "#ff8800"). Más alakra dobj `ValueError`-t.',
  "def hex_szin(s: str) -> list[int]", code(r'''
    import re


    def hex_szin(s):
        if not re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', s):
            raise ValueError(s)
        h = s[1:]
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
  '''),
  ("s: string): number[]", code(r'''
    if (!/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(s)) throw new RangeError(s);
    let h = s.slice(1);
    if (h.length === 3) h = [...h].map((c) => c + c).join('');
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  ''')),
  [(("#ff8800",), [255, 136, 0]), (("#f80",), [255, 136, 0])],
  [(("#000000",), [0, 0, 0]), (("#FFFFFF",), [255, 255, 255]), (("#1a2B3c",), [26, 43, 60]), (("#abc",), [170, 187, 204])],
  [("ff8800",), ("#ff880",), ("#ggg",), ("",), ("#ff88001",), ("#ff8800\n",)])
h(1, "median", ["py.collections", "py.errors"], "median", "Medián",
  "Írj `median(xs: list[float]) -> float` függvényt: a lista mediánja, vagyis számérték szerinti rendezés után páratlan elemszámnál a középső elem, párosnál a két középső számtani közepe. Üres listára dobj `ValueError`-t.",
  "def median(xs: list[float]) -> float", code(r'''
    def median(xs):
        if not xs:
            raise ValueError('üres')
        s = sorted(xs)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
  '''),
  ("xs: number[]): number", code(r'''
    if (!xs.length) throw new RangeError('üres');
    const s = [...xs].sort((a, b) => a - b);
    const n = s.length;
    return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
  ''')),
  [(([3, 1, 2],), 2), (([4, 1, 3, 2],), 2.5)],
  [(([5],), 5), (([10, -10],), 0), (([1, 1, 1, 1],), 1), (([-5, -1, -3],), -3), (([0.5, 1.5],), 1.0), (([1, 10, 2],), 2), (([10, 2, 38, 23, 38, 23, 21],), 23)],
  [([],)])
h(1, "modusz", ["py.collections"], "mode", "Módusz",
  "Írj `modusz(xs: list[int]) -> int | None` függvényt: a lista leggyakoribb eleme; ha több elem is ugyanannyiszor fordul elő, közülük a legkisebb. Üres listára `None`.",
  "def modusz(xs: list[int]) -> int | None", code(r'''
    from collections import Counter


    def modusz(xs):
        if not xs:
            return None
        c = Counter(xs)
        return min(c, key=lambda x: (-c[x], x))
  '''),
  ("xs: number[]): number | null", code(r'''
    if (!xs.length) return null;
    const c = new Map<number, number>();
    for (const x of xs) c.set(x, (c.get(x) ?? 0) + 1);
    let best = xs[0];
    for (const [x, k] of c) if (k > c.get(best)! || (k === c.get(best) && x < best)) best = x;
    return best;
  ''')),
  [(([1, 2, 2, 3],), 2), (([],), None)], [(([5],), 5), (([3, 1, 3, 1],), 1), (([-1, -1, 2, 2, 2],), 2), (([4, 4, -4, -4],), -4), (([7, 8, 9],), 7)])


# ── writer ────────────────────────────────────────────────────────────────────

def camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(x[:1].upper() + x[1:] for x in rest)


def yaml_text(canary, tid, t, lang, topics, prompt, sig, files) -> str:
    return (f"# {canary}\nid: {tid}\nlevel: {t['level']}\nlang: {lang}\ntopics: [{', '.join(topics)}]\ntitle_hu: {t['title']}\nprompt_hu: |\n"
            + textwrap.indent(textwrap.fill(prompt, 110, break_long_words=False, break_on_hyphens=False), "  ") + "\n"
            + f'signature: "{sig}"\nfiles: {files}\n'
            + "source: {kind: own, license: own}\nlimits: {wall_s: 20, mem_mb: 512}\nsplit: heldout\n"
            + f"family: {t['family']}\nrating: {1000 + 200 * t['level']}\n")


def ts_prompt(tid: str, prompt: str, sig: str) -> str:
    p = prompt.split("`", 2)
    text = p[0] + f"`{sig.removeprefix('export function ')}`" + p[2]  # the first code span is the signature
    for a, b in (*EXTRA_MAP, *PROMPT_MAP):
        text = text.replace(a, b)
    bad = [w for w in FORBIDDEN_H if w in text]
    assert not bad, f"{tid}: python idiom left in prompt: {bad}"
    return text


def write(d: Path, files: dict[str, str]) -> None:
    (d / "tests").mkdir(parents=True, exist_ok=True)
    (d / "ref").mkdir(exist_ok=True)
    for rel, text in files.items():
        (d / rel).write_text(text, encoding="utf-8", newline="\n")


def build() -> list[str]:
    counters: dict[tuple[str, int], int] = {}
    ids = []
    for t in H:
        for lang in ("py", "ts"):
            n = counters[(lang, t["level"])] = counters.get((lang, t["level"]), 0) + 1
            tid = f"{lang}-l{t['level']}-h-{n:04d}"
            canary = f"AURI-CANARY-{uuid.uuid5(NS, 'aurikod-hu-v1/' + tid)}"
            errs = [(a, V) for a in t["err"]]
            if lang == "py":
                fn = t["name"]
                files = {
                    "task.yaml": yaml_text(canary, tid, t, "py", t["topics"], t["prompt"], t["sig"],
                                           "{visible: tests/test_visible.py, hidden: tests/test_hidden.py, reference: ref/solution.py}"),
                    "tests/test_visible.py": test_file(canary, fn, "Visible", t["vis"], errs[:1], ""),
                    "tests/test_hidden.py": test_file(canary, fn, "Hidden", t["hid"], errs, ""),
                    "ref/solution.py": f"# {canary}\n# Reference solution: only for validating the task.\n{t['py']}",
                }
            else:
                fn = camel(t["name"])
                params, body = t["ts"]
                sig = f"export function {fn}({params}"
                body = textwrap.indent(body.strip("\n"), "  ")
                hidden_header = "// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.\n"
                files = {
                    "task.yaml": yaml_text(canary, tid, t, "ts", [TOPIC.get(x, x) for x in t["topics"]], ts_prompt(tid, t["prompt"], sig), sig,
                                           "{visible: tests/visible.test.ts, hidden: tests/hidden.test.ts, reference: ref/solution.ts}"),
                    "tests/visible.test.ts": TEST_TMPL.format(canary=canary, header="", fn=fn, cases=js([(list(a), w) for a, w in t["vis"]]),
                                                              errors=js([list(a) for a in t["err"][:1]]), extra=""),
                    "tests/hidden.test.ts": TEST_TMPL.format(canary=canary, header=hidden_header, fn=fn,
                                                             cases=js([(list(a), w) for a, w in t["hid"]]), errors=js([list(a) for a in t["err"]]),
                                                             extra=""),
                    "ref/solution.ts": f"// {canary}\n// Reference solution: only for validating the task.\n{sig} {{\n{body}\n}}\n",
                }
            write(ROOT / tid, files)
            raw = taskset.load_raw(ROOT / tid)  # validates; and the prompt must survive the YAML round trip intact
            want = textwrap.fill(ts_prompt(tid, t["prompt"], sig) if lang == "ts" else t["prompt"], 10**6)
            assert " ".join(raw["prompt_hu"].split()) == " ".join(want.split()), f"{tid}: prompt_hu changed in YAML"
            ids.append(tid)
    return ids


if __name__ == "__main__":
    manifest = ROOT / taskset.HELDOUT_MANIFEST
    if manifest.exists() and "--force" not in sys.argv:
        sys.exit(f"A heldout be van fagyasztva ({manifest}); új verzió = új azonosítók + új manifeszt.")
    assert sum(t["level"] == 0 for t in H) == 18 and len(H) == 60, (len(H), sum(t["level"] == 0 for t in H))
    assert len({t["name"] for t in H}) == 60
    out = build()
    hashes = taskset.heldout_hashes(ROOT)
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps({"taskset": "aurikod-hu-v1", "split": "heldout", "frozen": "2026-11-21", "tasks": len(out),
                                    "files": hashes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(len(out), "tasks:", out[0], "…", out[-1], "| manifest:", len(hashes), "files")
