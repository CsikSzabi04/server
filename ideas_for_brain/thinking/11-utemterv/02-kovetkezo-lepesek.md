# Következő lépések — így indul a P0

> **Miről szól:** a P0 (minimális programozási ciklus) elindításának konkrét 10 lépése: ki, mit, hol
> a repóban, mikor kész. Előtte a legkisebb hasznos változat (egy este), utána a teljes P0.
> A helyre és a technológiára vonatkozó javaslatok a [03-nyitott-kerdesek.md](03-nyitott-kerdesek.md) döntéseitől függnek.

## 1. A legkisebb hasznos változat (P0-mini)

Egy nyelv (Python — a `unittest` függőség nélkül fut), 3 saját L1-feladat, a gemma4:e2b, S0 sandbox
(futási mappa + időkorlát + Job Object + tiszta env + a tűzfalszabály, egyszeri admin lépés), ≤ 3 javítókör, SQLite-tár.

**Kész, ha:** `python -m auri_core run tasks/py-l1-0001` → vagy zöld megoldás a tárban, vagy őszinte bukás
a hibakivonattal; a második futtatás a tárból jön, LLM-hívás nélkül. Ráfordítás: ~1 este (becslés).
Ez **csak** Auri saját generálású kódjára, saját feladatokon futhat (S0 nem biztonsági határ).

## 2. Hely, szerkezet, közös sémák

Hely (NK1, egyezik a [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) javaslatával): `auri-core/`, Python 3.12
(a gépen 3.12.6). A P0-ban csak standard könyvtár + pytest; a Jarvis moduljai könyvtárként importálhatók.

```
auri-core/
  pyproject.toml
  auri_core/{__init__,__main__,contracts,llm,sandbox,digest,solve,store,bench}.py
  tasks/ts-l1-0007/{task.yaml, tests/visible.test.ts, tests/hidden.test.ts, ref/solution.ts}   # CodeTask
  tests/                    # a Core saját tesztjei: szökési próbák, kivonat, ciklus hamis LLM-mel
  data/                     # gitignore-olt: core.db, runs/<runId>/journal.jsonl
%LOCALAPPDATA%\Auri\sandbox\runs\<runId>\   # futási mappa a repón KÍVÜL
C:\AuriSandbox\runtime\                     # dedikált node.exe / python.exe a tűzfaltiltáshoz
```

A `contracts.py` **nem talál ki saját sémát** (a `JARVIS_BUILD.md` 2.1 tanulsága): a 06-os mappa közös
típusainak Python-tükre, és utána csak importálni szabad belőle.

| Séma | Forrás | Mire kell a P0-ban |
|---|---|---|
| `CodeTask` | [../06-programozas/08-gyakorlofeladatok.md](../06-programozas/08-gyakorlofeladatok.md) 1. pont | feladat: szint, nyelv, leírás, látható/rejtett teszt, `split` |
| `RunResult` | [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) 7. pont | egy sandbox-futás eredménye |
| `VerifiedSnippet` | [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) 2. pont | a zöld megoldás tárolva (T2), forrással, licenccel |
| `ErrorPattern` + `normalizeError` | [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md) 7. pont | hibaaláírás → javítás |
| `solve()` / `Outcome` | [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) 2. pont | a ciklus maga |

## 3. A 10 lépés

| # | Lépés | Ki | Hol | Kész, ha | Idő (becslés) |
|---|---|---|---|---|---|
| 1 | Döntések: NK1, NK2 (S0 + tűzfal), NK3 (alapvonal előbb), NK6, NK18 | felhasználó | [03-nyitott-kerdesek.md](03-nyitott-kerdesek.md) | van „Döntés:” sor | 15 perc |
| 2 | Váz + `contracts.py` (a közös sémák tükre) | ügynök | `auri-core/` | importálható; `pytest` fut | 0,5 nap |
| 3 | `aurikod-hu v1` `dev` része: 40 feladat/nyelv (TS, Python), L0–L1, canaryval | felhős kódoló ügynök ír (részben Exercism-konverzió, MIT), a felhasználó átnéz | `auri-core/tasks/` | minden referencia zöld a látható + rejtett teszteken; a csonk piros | 1–2 nap |
| 4 | S0 sandbox + szökési próbák | ügynök; a tűzfalszabályt (admin) a felhasználó hagyja jóvá | `auri_core/sandbox.py` | ld. 4. pont | 1 nap |
| 5 | LLM-kliens + a hiányzó mérések ([NK14](03-nyitott-kerdesek.md)): prefill, KV-cache-újrahasználat, JSON-arány, `num_thread`, megszakítás utáni sáv | ügynök | `auri_core/llm.py`, `bench.py` | az 1. token egyezik a `bench_llm.py` nagyságrendjével; az 5 új szám a tények lapján | 1 nap |
| 6 | Hibakivonat: `normalizeError` + tömörítés, zajszűrés (pl. `ExperimentalWarning`) | ügynök | `auri_core/digest.py` | node:test- és unittest-kimenetből egységes, ≤ 20 soros kivonat | 0,5 nap |
| 7 | A ciklus: `solve()` ≤ 3 javítással, JSONL-napló; nincs „kész” zöld `RunResult` nélkül | ügynök | `auri_core/solve.py` | hamis LLM-mel tesztelve: 3 kör, körbejárás, feladás | 1 nap |
| 8 | Tár + emlékezés: zöld → `VerifiedSnippet` (T2), bevált javítás → `ErrorPattern` | ügynök | `auri_core/store.py`, `data/core.db` | ugyanaz a feladat másodszor 0 LLM-hívással; csak zöld kerül be | 0,5 nap |
| 9 | Alapvonal: gemma4:e2b `model-only`, majd `+repair` a `dev`-en; a `heldout` (60/nyelv) megírva, befagyasztva, első hivatalos mérés | felhasználó hagyja jóvá a CPU-időt | `python -m auri_core bench …` | pass@1 és javítással@3 a fejlődési naplóban | ld. 5. pont |
| 10 | Értékelés: NK18 A/B, kódoló modell (NK3), a P0-kapu | felhasználó + ügynök | fejlődési napló, [01-fazisok.md](01-fazisok.md) | a P0 „Kész, ha” teljesül; döntés a P1 indításáról | 30 perc |

## 4. Az S0 sandbox próbái (4. lépés)

A teljes lista: [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) 8. pont. A P0-ban minimum:
végtelen ciklus → `timeout`, nincs árva folyamat; memóriafaló → leállítva; a környezetben **nincs** titok
(`.env`, `SUPABASE_*`, `*_API_KEY`); a futási mappán kívülre írás tiltva (Node: `--permission
--allow-fs-write=<futási mappa>` — a v24.14.0 ismeri, de **hálózati kapcsolója nincs**, ezért kell a
tűzfalszabály); kimenő hálózat → hiba; kimenet-korlát, hogy egy elszabadult `print` ne töltse meg a naplót.

## 5. Az alapmérés ideje

- **Alapvonal (`model-only`):** egy L1-generálás a gemma4:e2b-vel ~25–65 s (számolt becslés a mért
  6,2 tok/s-ból) → 2 × 40 `dev` feladat ~1–1,5 óra.
- **`+repair` és a `heldout`:** ~60 feladat/nyelv × 3–8 perc (becslés) = **nyelvenként ~3–8 óra** → több
  éjszakára bontva, csak tétlenségben (NK5). A `VOICE` (Jarvis hangkör) mindig megelőzi; a `BACKGROUND` futás azonnal
  átadja a sávot (mért versengés: közös sávon az 1. token medián 3,9 s, p90 14,0 s).
- Modellenként egyben fut (hideg betöltés mérve: e2b 18,5 s, e4b 31,5 s, qwen3.5:4b 38,3 s).

## 6. Szabályok az implementáló ügynöknek

- Csak az `auri-core/` mappát írja; a `web/**`, `auri-jarvis/**`, `server/**` **csak olvasható** (a Jarvis
  moduljai importálhatók, de nem módosíthatók). A `.gitignore` bővítése (`auri-core/data/`, `.venv/`) jóváhagyással.
- Python 3.12, típusannotációk, angol kód és kommentek, magyar felhasználói szöveg (mint a Jarvisban).
- Feladatokban, tesztekben csak fiktív adat („Teszt Elek”). Titok soha nem kerül naplóba.
- A `heldout` készletet a fejlesztés közben senki nem használja promptfejlesztésre (csak a `dev`-et).
- „Mérj, ne higgy”: minden állítás számmal kerül a fejlődési naplóba (minta, medián, p90).
- Több párhuzamos ügynöknél koordinációs tábla a `JARVIS_BUILD.md` mintájára; a P0-hoz egy ügynök elég.

## 7. Amit most szándékosan NEM csinálunk

Web-keresés, szerepek és vita, többfájlos projekt (L3–L4, S1 kell hozzá), HUD-panel, felhő, éjszakai
ütemező, kiköltöztetés a böngészőből. Mindegyiknek megvan a fázisa ([01-fazisok.md](01-fazisok.md)); a P0
mérései nélkül nem tudnánk, hogy segítenek-e.

## Kapcsolódó

- [01-fazisok.md](01-fazisok.md) · [03-nyitott-kerdesek.md](03-nyitott-kerdesek.md) · [../thinking.md](../thinking.md) (8. pont)
- [../06-programozas/01-cel-es-szintek.md](../06-programozas/01-cel-es-szintek.md) · [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md) (a P0 „Kész, ha” mérési része)
- [../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md](../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md) · [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md)
- [../07-komplex-feladatok/04-onellenorzes-es-javitas.md](../07-komplex-feladatok/04-onellenorzes-es-javitas.md) — a javítókör és a hibakivonat
