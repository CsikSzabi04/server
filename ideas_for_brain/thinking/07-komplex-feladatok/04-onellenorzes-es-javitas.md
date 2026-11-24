# Önellenőrzés és javítás — mikor javít, mikor kérdez, mikor adja fel

> **Miről szól:** mit tekint Auri bizonyítéknak, hogyan működik a hibából-javítás köre (≤ 3 kör),
> mire jó (és mire nem) a Kritikus modell, hogyan előzzük meg a „teszt-csalást” és a körbejárást,
> mikor kérdezi meg a felhasználót, és mikor mondja ki őszintén, hogy nem sikerült.

## 1. A bizonyítékok rangsora

| Rang | Forrás | Mit ér |
|---|---|---|
| 1 | lefuttatott teszt / smoke a sandboxban | **bizonyíték** |
| 2 | fordító, típusellenőrző, linter | bizonyíték a formára, nem a helyességre |
| 3 | determinisztikus őr (hash, tiltott import, tesztszám) | bizonyíték a szabálykövetésre |
| 4 | Kritikus modell (indoklással, sorhivatkozással) | **hipotézis** — csak akkor kapu, ha bukó tesztté alakítható |
| 5 | a modell önértékelése („szerintem jó”) | nem számít |

Elv: **a modell véleménye nem bizonyíték.** A kis modellek magabiztosan tévednek, és két kis modell
könnyen egyetért ugyanabban a tévedésben.

## 2. A hibakivonat (amit a javító modell kap)

A nyers kimenet (több száz sor stack trace) helyett tömör, normalizált kivonat:

```ts
interface FailureDigest {
  check: 'parse' | 'guard' | 'typecheck' | 'test' | 'smoke';
  signature: string;          // normalizált: hibatípus + első projektfájlbeli frame + üzenet, számok/útvonalak nélkül
  failing: number; total: number;
  first?: { test: string; expected?: string; actual?: string };
  location?: { file: string; line: number };
  excerpt: string;            // ≤ 20 sor, csak projektfájlok frame-jei; titok/útvonal maszkolva
}
```

Csak az **első** bukó tesztet részletezzük — kis modell egyszerre egy hibát javít jól (becslés,
a P0-ban mérjük). Az `excerpt` adat, nem utasítás: a futtatott kód kimenete is tartalmazhat prompt-injekciót.

## 3. A javító kör

```python
def repair_loop(task, ws, digest, llm, kb, max_rounds=3):
    seen = {digest.signature}
    best = (digest.failing, ws.read(task.writes))                # a legjobb eddigi változat
    for rnd in range(1, max_rounds + 1):
        hints = kb.fix_patterns(digest.signature, k=2)          # korábbi, ellenőrzött hiba→javítás párok
        out = llm.fix(task.brief, current=best[1], digest=digest, hints=hints)
        if violates_guard(out, task):                            # befagyasztott fájl, teszt kikapcsolása…
            journal.log("repair.rejected", rnd); continue        # ez is egy kör
        ws.write(out)
        new = verify(task, ws)
        if new is None:
            kb.record_fix(before=digest, after_code=out, verified=True); return "ok"
        if new.signature in seen:                                # ugyanaz a hiba újra → körbejár
            ws.write(best[1]); return "escalate"
        if new.failing <= best[0]:
            best, digest = (new.failing, out), new               # haladás: ebből javítunk tovább
        else:
            ws.write(best[1])                                    # rosszabb lett: vissza a legjobbra, a régi kivonattal
        seen.add(new.signature)
    return "escalate"
```

- **Kis fájlnál (≤ ~80 sor) teljes fájl a kimenet**, nem diff — a kis modellek a diff-formátumot
  gyakran elrontják (becslés; a P0-ban összemérjük a kettőt).
- **Haladás** = csökken a bukó tesztek száma, vagy új aláírás jön (továbbjutott a következő hibáig).
- Ugyanaz az aláírás kétszer → nincs értelme egy negyedik körnek ugyanazzal a modellel.

## 4. Teszt-csalás elleni őr

A kis modell hajlamos a legrövidebb utat választani a zöldhöz. Determinisztikus tiltások:

- a tesztfájl a kód-feladat alatt **befagyasztott** (hash-ellenőrzés);
- a tesztek és az `assert`-ek száma nem csökkenhet; nincs `.skip`, `.only`, `@unittest.skip`, `pytest.mark.skip`;
- nincs tesztkörnyezet-figyelés (`process.env.NODE_TEST_CONTEXT`, `"unittest" in sys.modules`);
- gyanújel a Kritikusnak: a tesztben szereplő konkrét bemenet szó szerint feltételként jelenik meg a kódban
  (`if (title === 'Teszt Elek')`) → kemény kódolás gyanúja.

## 5. A Kritikus: mikor és hogyan

Ott hasznos, ahol **nincs** teszt (terv, szerződés, README, magyarázat), vagy ahol a tesztet magát kell
megkérdőjelezni. Kimenete kötött JSON, sorhivatkozással:

```json
{ "issues": [ { "severity": "high", "file": "src/app.js", "line": 42,
  "claim": "DELETE nem létező id-re 204-et ad 404 helyett", "proposed_test": "DELETE /todos/999 → 404" } ] }
```

- Egy `high` állítás **csak akkor kapu**, ha a `proposed_test` lefut és **elbukik** a mostani kódon →
  valódi hiba, a teszt a készletbe kerül (a Tesztelő ellenőrzi, hogy a szerződéssel egyezik-e).
- Ha a javasolt teszt zöld, a kritika téves volt → eldobjuk, és mérjük a **Kritikus pontosságát**
  (igazolt / összes állítás) — ez dönti el, megéri-e futtatni ([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).
- A Kritikus egyben, a futás végén fut (a prefixváltás mért ára miatt: e2b ~6 s, e4b ~17 s).

## 6. Az eszkalációs létra

| Fok | Mit csinál | Feltétel |
|---|---|---|
| 1 | javítás ugyanazzal a modellel (≤ 3 kör) | mindig |
| 2 | javítás **több tudással**: hibaminta a kódtudástárból, dokumentáció-kivonat, webes keresés a hibaüzenetre | ismeretlen hibaüzenet, API-gyanú |
| 3 | erősebb helyi modell (pl. e4b vagy kódoló modell, ha telepítve); a váltás ára a hideg betöltés (mért: e4b 31,5 s, qwen3.5:4b 38,3 s) | 1–2 nem hozott haladást |
| 4 | felhős modell (Groq / Gemini) | **csak** ha a felhasználó engedélyezte, és a kódban nincs titok / személyes adat |
| 5 | kérdés a felhasználónak | ld. 7. pont |
| 6 | őszinte feladás részeredménnyel | ld. 8. pont |

## 7. Mikor kérdez a felhasználótól?

| Helyzet | Példa kérdés (egy kérdés, opciók, **egy javaslat**) |
|---|---|
| a követelmény kétértelmű, és drága lenne rosszul dönteni | „Kell felhasználónkénti todo-lista (auth)? A) nem, B) igen. Javaslom: A.” |
| szerződés-döntés kompromisszummal | „ID: egész szám vagy UUID? Javaslom: egész szám (egyszerűbb SQLite-ban).” |
| csomag kell az engedélylistán kívülről | „A `zod` nincs az engedélylistán. Felvegyem? Javaslom: nem, kézi validáció elég.” |
| hálózat, titok, rendszerszintű művelet kellene | mindig kérdés, sosem magától |
| a keret elfogyott | „45 perc ment el, 7/9 feladat kész. Folytassam még 20 percig?” |

Nem kérdez arról, amit egy ésszerű alapértelmezés eldönt — azt **feltételezésként** a jelentésbe írja.

## 8. Mikor adja fel — és hogyan

Feladás, ha: a létra 1–3. foka nem hozott haladást, a 4–5. nem elérhető (vagy a felhasználó nem
válaszol), vagy a futás kerete elfogyott. A jelentés **a naplóból** készül (nem a modell fogalmazza a tényeket):

```
❌ Nem sikerült teljesen: todo API — 7/9 feladat kész, 14/17 teszt zöld.
Elakadt: F6 (src/app.js) — „PATCH /todos/:id üres testtel → 400 helyett 500”, 3 kör + e4b után is.
Megvan és működik: tárolási réteg (6/6 teszt), szerződés, váz. A munkaterület: <útvonal>.
Javaslat: nézd meg a validációt; vagy engedélyezd a felhős segítséget erre az egy fájlra.
```

## 9. Mi kerül a tudástárba?

| Kimenet | Mit tárolunk (közös sémák: [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md), [06-hibakereses](../06-programozas/06-hibakereses.md)) | Bizalom |
|---|---|---|
| zöld megoldás | `VerifiedSnippet`: kód + tesztek + `RunResult` hivatkozás | T2 (tesztelt); T3, ha rejtett teszt is igazolja és ≥ 3-szor bevált |
| sikeres javítás | `ErrorPattern`: hibaaláírás → ok → javítás, `worked` számlálóval | a sandboxban bevált javítás emeli |
| sikertelen próba | csak a naplóban, „negatív példaként” | — (nem tudás) |
| a Kritikus igazolt állítása | új teszt a készletben | — (teszt, nem tudás) |
| a Kritikus nem igazolt állítása | semmi — modellbizonyítékkal semmi nem lesz `verified` | — |

## 10. Kész, ha

- Ugyanaz a hiba kétszer → a kör megáll és eszkalál (egységteszt hamis modellel).
- Teszt kikapcsolása, `assert` törlése, befagyasztott fájl írása → 100%-ban elutasítva (őr-tesztek).
- A Kritikus pontossága mérve van a P0/P3 készletén; ha < 50% (célérték, becslés), alapból ki van kapcsolva.
- Minden feladásnál a jelentés tartalmazza: mi kész, mi nem, az utolsó hiba, hol a munkaterület, egy javaslat.

## Kapcsolódó

- [02-terv-vegrehajtas-ellenorzes.md](02-terv-vegrehajtas-ellenorzes.md) · [05-teljes-pelda.md](05-teljes-pelda.md)
- [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md) — hibakeresési stratégiák részletesen
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) · [../02-belso-parbeszed/02-vita-protokoll.md](../02-belso-parbeszed/02-vita-protokoll.md)
- [../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)
- [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md) — a futási kimenet is adat
- [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
