# Mit jelent itt „gondolkodni”?

> **Miről szól:** a „gondolkodás” működő, mérhető definíciója Auri számára — nem érzés és nem varázslat,
> hanem ellenőrizhető lépések sorozata. A gondolkodás fajtáit (gyors, lassú, tervezés, reflexió,
> metakogníció…) konkrét mechanizmusokra, komponensekre és fázisokra képezzük le.

## 1. Működő definíció

Auri akkor **gondolkodik**, ha egy cél felé **több, egymásra épülő lépést** tesz, és minden lépés:

1. **felhasználja**, amit már tud (tudástár, korábbi epizódok, tanulságok),
2. **nyomot hagy** (epizódnapló: mit tett, miért, melyik modellel, mennyi idő alatt),
3. **ellenőrizhető** eredményt ad (lefutott teszt, egyező források, a felhasználó visszajelzése),
4. és a végén **változtat a tudásán** (tanulság, új vagy megerősített tudáselem).

Ami ebből kimarad, az szöveggenerálás, nem gondolkodás. Konkrétan **nem számít gondolkodásnak**:

- a mai kulcsszavas + Markov-válasz (`web/src/brain/learn.ts` `generate()`, `answer.ts` 6. szintje):
  nincs cél, nincs ellenőrzés;
- egy modell egyetlen, ellenőrizetlen válasza — ez **hipotézis**, amíg valami meg nem erősíti;
- a modell saját válaszának ellenőrzés nélküli eltárolása (ma ezt teszi a `distill.ts`) — ez
  önmegerősítő hibaforrás ([02-oszinte-korlatok.md](02-oszinte-korlatok.md), 5. pont).

## 2. A gondolkodás fajtái → konkrét mechanizmusok

| Fajta | Mit jelent itt | Mechanizmus | Komponens | Fázis | Mérőszám |
|---|---|---|---|---|---|
| **Gyors** („reflex”) | ismert dolgot azonnal felismer | cache, fast-path (regex + fuzzy), ellenőrzött tudástár-találat | Router, Memória | P0–P1 | cache-találati arány, válaszidő |
| **Lassú** | új vagy nehéz feladat lépésenként | a gondolkodó ciklus modellhívásokkal; `think` mód csak háttérben | Gondolkodók, ciklusvezérlő | P0 | sikerarány, LLM-másodperc / feladat |
| **Tervezés** | mit, milyen sorrendben, mi bizonyítja a „kész”-t | terv JSON-ban, minden lépéshez ellenőrzési pont | Gondolkodó (tervező prompt) | P0 (1 lépés), P5 | a terv lépéseinek teljesülése |
| **Külső ellenőrzés** | működik-e, igaz-e | sandbox-tesztek, fordító, források egyezése | Ellenőrző / Sandbox, Web-szörföző | P0, P2 | zöld tesztek aránya |
| **Kritika** (belső) | más szemmel ránéz | Kritikus szerep, ellenpélda-keresés | Gondolkodók | P3 | talált valódi hibák / hamis riasztások |
| **Reflexió** | mi működött, mi nem, miért | tanulság-lépés: rövid, szerkezett jegyzet az epizódból | ciklusvezérlő → Memória | P0 (egyszerű), P3 | újrahasznosított tanulságok |
| **Metakogníció** | tudja, mit tud és mit nem | lefedettség + bizalom + korábbi sikerarány → nehézségbecslés, keret, „kérdezek / feladom” | Router, Ütemező | P1–P2 | kalibráció (becsült vs. tényleges siker) |
| **Kíváncsiság** | magától keres tudáshiányt | hiánylista (bukott epizódok, alacsony lefedettség) → tananyag | Tananyag-kezelő | P4 | a hiánylista fogyása |
| **Konszolidáció** („alvás”) | rendet rak a fejében | duplikátum-összevonás, ismétlés, elavultak jelölése | Ütemező + Memória | P4 | duplikátumarány, elavult találatok |

Ugyanaz a gondolkodó ciklus valósítja meg mindet; a fajták abban különböznek, **meddig jut** a ciklus
és **mennyi keretet** kap ([../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md)).

## 3. Gyors út vagy lassú út?

```python
async def think(goal: Goal) -> Outcome:
    hit = await memory.lookup_verified(goal)            # gyors: cache + ellenőrzött tudástár
    if hit and hit.trust >= 0.8 and not hit.stale:       # 0.8: becslés, kalibrálni kell
        return Outcome.from_memory(hit)                  # nincs modellhívás
    if fastpath.match(goal.text):                        # determinisztikus eszköz (idő, számolás…)
        return await fastpath.run(goal)
    a = assess(goal)                                     # metakogníció, ld. 4. pont
    if a.needs_clarification and goal.interactive:
        return Outcome.ask_user(a.question)              # egy rövid kérdés, nem találgatás
    return await loop.run(goal, budget=a.budget, start_level=a.level)   # lassú út
```

A gyors út **csak ellenőrzött** tudásból dolgozhat. Hipotézist a gyors út nem ad vissza válaszként —
legfeljebb a lassú út kiindulópontja lehet („korábban ezt gondoltam, ellenőrizzük”).

## 4. Metakogníció: a „tudom / nem tudom” jel

A kis modellek **magabiztosan tévednek** (mért példa: „Ausztrália fővárosa: Sydney”, ld.
[03-tenyek-es-meresek.md](03-tenyek-es-meresek.md)), ezért a modell önbizalma **nem** jel. A
metakogníció külső, számolható jelekből áll:

```python
@dataclass
class Assessment:
    kind: Literal["chat", "code", "research", "study"]
    known_ratio: float        # a kérdés kulcsfogalmaiból hányat fed le ellenőrzött tudás (0..1)
    similar_success: float    # hasonló korábbi epizódok sikeraránya (0..1; nincs adat → 0.5)
    freshness_risk: bool      # verziófüggő / gyorsan változó téma (könyvtár-API, árak, hírek)
    needs_web: bool
    needs_clarification: bool
    question: str | None      # az egyetlen pontosító kérdés, ha kell
    level: int                # a router induló szintje (L0–L4)
    budget: Budget            # LLM-hívás, token, idő, javítási kör
```

A becslés minőségét is mérjük: ha Auri azt mondta, „80% eséllyel megy”, akkor az ilyen feladatok kb.
80%-ának tényleg sikerülnie kell (**kalibráció**, [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

## 5. Példa végig: „Írj Python-függvényt, ami ékezetes magyar címből URL-barát slugot csinál”

| Lépés | Mi történik | Idő (becslés) |
|---|---|---|
| 1. Emlékezés | Kódtudástár: nincs `slugify` teszttel; részleges találat: egy jegyzet a `unicodedata.normalize("NFKD")`-ről | < 1 s |
| 2. Megértés | Önkérdezés: mi az elválasztó? kisbetű? mi legyen a szóközsorozatból? Interaktív módban legfeljebb **egy** kérdés, különben észszerű alapértelmezés + kimondva | 0–10 s |
| 3. Terv | Egy lépés: előbb 5 teszteset (pl. „Árvíztűrő tükörfúrógép” → `arvizturo-tukorfurogep`), utána a kód | modellhívás része |
| 4. Cselekvés | A modell megírja a teszteket és a függvényt (~250 token ≈ 40 s a mért 6,2 tok/s-mal, gemma4:e2b) | ~40–60 s |
| 5. Ellenőrzés | Sandbox: `pytest` → 4/5 zöld; a „  több   szóköz  ” eset `--tobb---szokoz--` lett (várt: `tobb-szokoz`) | 1–3 s |
| 6. Javítás | Hibaüzenet + kód vissza a modellnek → összevonja a kötőjeleket, levágja a széleket → 5/5 zöld | ~30–60 s |
| 7. Tanulság | „Slug: a szóközsorozatot és a szélső elválasztót mindig kezelni kell — gyakori hiba.” | ~10 s |
| 8. Megjegyzés | Kód + tesztek → kódtudástár, `verified` (`tests_passed`), forrás: ez az epizód | < 1 s |

Legközelebb ugyanez a kérés: **cache-találat** + a tárolt tesztek újrafuttatása (néhány másodperc) —
modellhívás nélkül. Ez az „okosodás” valódi forrása.

## 6. Amit nem állítunk

- Nem állítjuk, hogy Auri „ért” vagy „tudatos” — **viselkedést mérünk**: sikerarány, idő, hibák.
- A modellek súlyai nem változnak. A fejlődés a **tudástárból, a tapasztalatból (epizódokból) és a
  jobb útvonalválasztásból** jön ([../thinking.md](../thinking.md), 2. pont).
- Egy lépés, amit nem lehet ellenőrizni, attól még lehet hasznos, de a kimenete hipotézis marad, és
  Auri ezt ki is mondja („nem ellenőriztem”).

## Kapcsolódó

- [../thinking.md](../thinking.md) — a térkép és a ciklus áttekintése
- [02-oszinte-korlatok.md](02-oszinte-korlatok.md) — miért kell az ellenőrzés
- [03-tenyek-es-meresek.md](03-tenyek-es-meresek.md) — a mért számok
- [04-fogalomtar.md](04-fogalomtar.md) — a fogalmak egy helyen
- [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) — a ciklus részletesen
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) — a belső szerepek és a szerepkönyv
- [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) — tesztek először
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — nehézségbecslés és szintek
- [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) — kalibráció és sikerarány
