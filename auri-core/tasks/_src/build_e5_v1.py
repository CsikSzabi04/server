"""E5 v1: multi-file Python mini-projects for the P5 planner measurement (bench --suite e5). Owner: AI-2.

Run:  .venv\\Scripts\\python.exe tasks\\_src\\build_e5_v1.py   → tasks/e5/E5-0N/{goal_hu.md, meta.json, accept/test_e5_accept.py}
The goal names every file and function (root of the workspace), so the hidden acceptance test can import them;
it checks only what the goal states. The planner never sees accept/ (only bench reads it, like hidden tests).
Not a task.yaml split: tasks/e5/ has no task.yaml, taskset.task_dirs ignores it.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "e5"
P: list[dict] = []


def project(pid, title, goal, acceptance, test, ref):
    P.append({"id": pid, "title": title, "goal": textwrap.dedent(goal).strip(), "acceptance": acceptance,
              "test": textwrap.dedent(test).strip() + "\n", "ref": {k: textwrap.dedent(v).strip() + "\n" for k, v in ref.items()}})


project("E5-01", "Bevásárlólista", '''
    Készíts egy kis Python bevásárlólista-projektet a munkakönyvtár gyökerében, két modulból (csak standard könyvtár).
    1. `lista.py`: `hozzaad(lista: dict[str, int], nev: str, db: int) -> None` — a nev tételhez db darabot ad (ha még nincs, felveszi); db < 1 esetén `ValueError`. `torol(lista: dict[str, int], nev: str) -> None` — eltávolítja a tételt; ha nincs ilyen, `KeyError`. `osszesen(lista: dict[str, int]) -> int` — az összes darabszám.
    2. `formaz.py`: `szoveg(lista: dict[str, int]) -> str` — soronként "név: db", név szerint növekvő sorrendben (a Python alapértelmezett szövegrendezése), a sorok között "\\n", a végén nincs sortörés; üres listára üres szöveg.
    Írj hozzájuk unittest-teszteket is.
''', ["lista.py: hozzaad / torol / osszesen a leírt módon, hibákkal", "formaz.py: szoveg név szerint rendezve", "a tesztek zöldek"], r'''
    import unittest

    from formaz import szoveg
    from lista import hozzaad, osszesen, torol


    class TestElfogadas(unittest.TestCase):
        def test_hozzaad_osszesen(self) -> None:
            lst: dict[str, int] = {}
            hozzaad(lst, "tej", 2)
            hozzaad(lst, "kenyér", 1)
            hozzaad(lst, "tej", 3)
            self.assertEqual(lst, {"tej": 5, "kenyér": 1})
            self.assertEqual(osszesen(lst), 6)

        def test_hibak(self) -> None:
            lst = {"tej": 1}
            with self.assertRaises(ValueError):
                hozzaad(lst, "alma", 0)
            with self.assertRaises(KeyError):
                torol(lst, "alma")
            torol(lst, "tej")
            self.assertEqual(lst, {})

        def test_szoveg(self) -> None:
            self.assertEqual(szoveg({"tej": 2, "alma": 3}), "alma: 3\ntej: 2")
            self.assertEqual(szoveg({}), "")
''', {"lista.py": r'''
    def hozzaad(lista, nev, db):
        if db < 1:
            raise ValueError(db)
        lista[nev] = lista.get(nev, 0) + db


    def torol(lista, nev):
        del lista[nev]


    def osszesen(lista):
        return sum(lista.values())
''', "formaz.py": r'''
    def szoveg(lista):
        return "\n".join(f"{k}: {v}" for k, v in sorted(lista.items()))
'''})
project("E5-02", "Jegyzetkereső", '''
    Készíts egy kis Python jegyzetkereső-projektet a munkakönyvtár gyökerében, két modulból (csak standard könyvtár).
    1. `index.py`: `szavak(szoveg: str) -> list[str]` — a kisbetűsített szöveg betűkből és számjegyekből (`str.isalnum()`) álló, összefüggő karaktersorozatai, sorrendben. `epit(dokumentumok: dict[str, str]) -> dict[str, list[str]]` — minden szóhoz azon dokumentum-azonosítók növekvően rendezett, ismétlés nélküli listája, amelyekben a szó előfordul.
    2. `kereso.py`: `keres(index: dict[str, list[str]], lekerdezes: str) -> list[str]` — azon dokumentumok növekvően rendezett listája, amelyekben a lekérdezés minden szava (az `index.szavak` szerint) előfordul; ha a lekérdezésben nincs szó, üres lista.
    Írj hozzájuk unittest-teszteket is.
''', ["index.py: szavak és epit a leírt módon", "kereso.py: keres ÉS-kapcsolattal", "a tesztek zöldek"], r'''
    import unittest

    from index import epit, szavak
    from kereso import keres

    DOCS = {"a": "alma körte", "b": "Körte, szilva!", "c": "alma alma"}


    class TestElfogadas(unittest.TestCase):
        def test_szavak(self) -> None:
            self.assertEqual(szavak("Alma, KÖRTE! 3 db"), ["alma", "körte", "3", "db"])
            self.assertEqual(szavak(""), [])

        def test_epit(self) -> None:
            self.assertEqual(epit(DOCS), {"alma": ["a", "c"], "körte": ["a", "b"], "szilva": ["b"]})

        def test_keres(self) -> None:
            idx = epit(DOCS)
            self.assertEqual(keres(idx, "körte"), ["a", "b"])
            self.assertEqual(keres(idx, "alma körte"), ["a"])
            self.assertEqual(keres(idx, "ALMA"), ["a", "c"])
            self.assertEqual(keres(idx, "barack"), [])
            self.assertEqual(keres(idx, " ,"), [])
''', {"index.py": r'''
    def szavak(szoveg):
        out, cur = [], ""
        for c in szoveg.lower():
            if c.isalnum():
                cur += c
            elif cur:
                out.append(cur)
                cur = ""
        if cur:
            out.append(cur)
        return out


    def epit(dokumentumok):
        idx = {}
        for doc_id, text in dokumentumok.items():
            for w in set(szavak(text)):
                idx.setdefault(w, []).append(doc_id)
        return {w: sorted(ids) for w, ids in idx.items()}
''', "kereso.py": r'''
    from index import szavak


    def keres(index, lekerdezes):
        ws = szavak(lekerdezes)
        if not ws:
            return []
        return sorted(set.intersection(*[set(index.get(w, [])) for w in ws]))
'''})
project("E5-03", "Pénztár", '''
    Készíts egy kis Python pénztár-projektet a munkakönyvtár gyökerében, három modulból (csak standard könyvtár).
    1. `ar.py`: `brutto(netto: int, afa: int) -> int` — a nettó forintár és az áfakulcs (százalék, pl. 27) alapján a bruttó ár egész forintra kerekítve, a fél forintot felfelé (pl. 50 Ft és 27% → 63,5 → 64). Ha netto < 0 vagy afa < 0, `ValueError`.
    2. `kosar.py`: `vegosszeg(tetelek: list[tuple[int, int, int]]) -> int` — a tételek (nettó, áfakulcs, darab) hármasok; a végösszeg a tételenkénti bruttó egységár (az `ar.brutto` szerint) és a darab szorzatának összege.
    3. `nyugta.py`: `nyugta(tetelek: list[tuple[int, int, int]]) -> list[str]` — tételenként egy sor "<db> x <bruttó egységár> Ft = <db · bruttó egységár> Ft", a végén egy "ÖSSZESEN: <végösszeg> Ft" sor.
    Írj hozzájuk unittest-teszteket is.
''', ["ar.py: brutto fél forintra felfelé kerekítve, hibával", "kosar.py: vegosszeg", "nyugta.py: a leírt sorok", "a tesztek zöldek"], r'''
    import unittest

    from ar import brutto
    from kosar import vegosszeg
    from nyugta import nyugta

    T = [(100, 27, 2), (50, 27, 1)]


    class TestElfogadas(unittest.TestCase):
        def test_brutto(self) -> None:
            self.assertEqual([brutto(100, 27), brutto(50, 27), brutto(10, 5), brutto(0, 27), brutto(2, 27)], [127, 64, 11, 0, 3])
            for args in ((-1, 27), (1, -5)):
                with self.assertRaises(ValueError):
                    brutto(*args)

        def test_vegosszeg(self) -> None:
            self.assertEqual(vegosszeg(T), 318)
            self.assertEqual(vegosszeg([]), 0)

        def test_nyugta(self) -> None:
            self.assertEqual(nyugta(T), ["2 x 127 Ft = 254 Ft", "1 x 64 Ft = 64 Ft", "ÖSSZESEN: 318 Ft"])
            self.assertEqual(nyugta([]), ["ÖSSZESEN: 0 Ft"])
''', {"ar.py": r'''
    def brutto(netto, afa):
        if netto < 0 or afa < 0:
            raise ValueError((netto, afa))
        return (netto * (100 + afa) + 50) // 100
''', "kosar.py": r'''
    from ar import brutto


    def vegosszeg(tetelek):
        return sum(brutto(n, a) * db for n, a, db in tetelek)
''', "nyugta.py": r'''
    from ar import brutto
    from kosar import vegosszeg


    def nyugta(tetelek):
        sorok = [f"{db} x {brutto(n, a)} Ft = {db * brutto(n, a)} Ft" for n, a, db in tetelek]
        return [*sorok, f"ÖSSZESEN: {vegosszeg(tetelek)} Ft"]
'''})
project("E5-04", "Hőmérséklet-napló", '''
    Készíts egy kis Python hőmérsékletnapló-projektet a munkakönyvtár gyökerében, két modulból (csak standard könyvtár).
    1. `naplo.py`: `beolvas(sorok: list[str]) -> list[tuple[str, float]]` — minden jó sor "ÉÉÉÉ-HH-NN hőmérséklet" alakú, egy szóközzel (pl. "2026-11-21 4.5"; a hőmérséklet tizedestört vagy egész, lehet negatív). A dátum pontosan 4-2-2 számjegy kötőjellel (naptár szerinti érvényességét nem kell nézni). A hibás sorokat (rossz dátumforma, nem szám, hiányzó rész, üres sor) kihagyja; a jókat (dátum, hőmérséklet float-ként) párokként, a bemenet sorrendjében adja vissza.
    2. `statisztika.py`: `napi(meresek: list[tuple[str, float]]) -> dict[str, tuple[float, float, float]]` — naponként (minimum, maximum, átlag), az átlag két tizedesre kerekítve (`round`).
    Írj hozzájuk unittest-teszteket is.
''', ["naplo.py: beolvas a hibás sorok kihagyásával", "statisztika.py: napi (min, max, átlag)", "a tesztek zöldek"], r'''
    import unittest

    from naplo import beolvas
    from statisztika import napi

    SOROK = ["2026-11-21 4.5", "2026-11-21 -1", "rossz sor", "2026-11-22 10", "2026-11-22 abc", "", "26-11-22 3", "2026-11-22"]


    class TestElfogadas(unittest.TestCase):
        def test_beolvas(self) -> None:
            self.assertEqual(beolvas(SOROK), [("2026-11-21", 4.5), ("2026-11-21", -1.0), ("2026-11-22", 10.0)])
            self.assertEqual(beolvas([]), [])

        def test_napi(self) -> None:
            m = [("2026-11-21", 4.5), ("2026-11-21", -1.0), ("2026-11-22", 10.0)]
            self.assertEqual(napi(m), {"2026-11-21": (-1.0, 4.5, 1.75), "2026-11-22": (10.0, 10.0, 10.0)})
''', {"naplo.py": r'''
    import re


    def beolvas(sorok):
        out = []
        for s in sorok:
            m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (-?\d+(?:\.\d+)?)", s)
            if m:
                out.append((m.group(1), float(m.group(2))))
        return out
''', "statisztika.py": r'''
    def napi(meresek):
        napok = {}
        for d, t in meresek:
            napok.setdefault(d, []).append(t)
        return {d: (min(v), max(v), round(sum(v) / len(v), 2)) for d, v in napok.items()}
'''})
project("E5-05", "Szóstatisztika", '''
    Készíts egy kis Python szóstatisztika-projektet a munkakönyvtár gyökerében, három modulból (csak standard könyvtár).
    1. `szamlalo.py`: `szamol(szoveg: str) -> dict[str, int]` — a `str.split()` szerinti szavak előfordulásai kisbetűsítve; minden szó elejéről és végéről levágja a `.,!?;:` írásjeleket, és ami így üres lesz, kimarad.
    2. `top.py`: `top(szamok: dict[str, int], n: int) -> list[tuple[str, int]]` — az n leggyakoribb szó (szó, darab) párokként, darabszám szerint csökkenő, egyenlőségnél szó szerint növekvő sorrendben; n ≤ 0 esetén üres lista.
    3. `main.py`: `futtat(szoveg: str, n: int) -> str` — a szöveg top n szava soronként "szó: darab" alakban, a sorok között "\\n", a végén nincs sortörés.
    Írj hozzájuk unittest-teszteket is.
''', ["szamlalo.py: szamol írásjelek levágásával", "top.py: top rendezéssel", "main.py: futtat", "a tesztek zöldek"], r'''
    import unittest

    from main import futtat
    from szamlalo import szamol
    from top import top


    class TestElfogadas(unittest.TestCase):
        def test_szamol(self) -> None:
            self.assertEqual(szamol("Alma, alma! Körte. ?"), {"alma": 2, "körte": 1})
            self.assertEqual(szamol(""), {})

        def test_top(self) -> None:
            self.assertEqual(top({"b": 2, "a": 2, "c": 5}, 2), [("c", 5), ("a", 2)])
            self.assertEqual(top({}, 3), [])
            self.assertEqual(top({"a": 1}, 0), [])

        def test_futtat(self) -> None:
            self.assertEqual(futtat("x y x. Y z!", 2), "x: 2\ny: 2")
''', {"szamlalo.py": r'''
    def szamol(szoveg):
        out = {}
        for w in szoveg.split():
            t = w.lower().strip(".,!?;:")
            if t:
                out[t] = out.get(t, 0) + 1
        return out
''', "top.py": r'''
    def top(szamok, n):
        return sorted(szamok.items(), key=lambda kv: (-kv[1], kv[0]))[:max(0, n)]
''', "main.py": r'''
    from szamlalo import szamol
    from top import top


    def futtat(szoveg, n):
        return "\n".join(f"{w}: {db}" for w, db in top(szamol(szoveg), n))
'''})


if __name__ == "__main__":
    for p in P:
        d = ROOT / p["id"]
        (d / "accept").mkdir(parents=True, exist_ok=True)
        (d / "goal_hu.md").write_text(p["goal"] + "\n", encoding="utf-8", newline="\n")
        meta = {"id": p["id"], "title": p["title"], "lang": "py", "acceptance": p["acceptance"], "limits": {"wall_s": 60}}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        (d / "accept" / "test_e5_accept.py").write_text(p["test"], encoding="utf-8", newline="\n")
        (d / "ref").mkdir(exist_ok=True)
        for name, body in p["ref"].items():  # reference workspace: validates the acceptance test (tests/hands)
            (d / "ref" / name).write_text(body, encoding="utf-8", newline="\n")
    print(len(P), "E5 projects →", ROOT)
