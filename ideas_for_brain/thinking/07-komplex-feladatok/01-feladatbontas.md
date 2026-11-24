# Feladatbontás — a céltól az ellenőrizhető lépésig

> **Miről szól:** hogyan bont Auri egy nagy kérést (pl. „írj egy REST API-t tesztekkel”) olyan apró,
> egyenként **gépileg ellenőrizhető** lépésekre, amiket egy CPU-n futó kis modell is megbízhatóan
> megcsinál. Adatszerkezet (DAG), méretezési szabályok, „szerződés először” elv, ki készíti a tervet.

## 1. Miért kell bontani

Egy kis helyi modell rövid, jól körülhatárolt feladatban használható, hosszú, sokfájlos feladatban
szétesik: elfelejti a korábbi döntéseket, importokat talál ki, a fájlok nem illeszkednek. A generálás
drága is: a gemma4:e2b mért **~6,2 tok/s**-ával egy ~3000 tokenes (≈300 soros, becslés) kimenet ~8 perc
— és ha a végén hibás, mind elveszett. A bontás négy dolgot ad: **egy lépés = egy gépileg ellenőrizhető
kimenet**; a hiba **helyi marad**; minden lépés **kis kontextust** kap; és **már ellenőrzött** alapra épül.

## 2. A négy szint

| Szint | Példa (todo API) | Ki állítja elő | Ellenőrzés | Darabszám |
|---|---|---|---|---|
| **Cél** (`Goal`) | „Node+Express+SQLite todo REST API tesztekkel” | a felhasználó | elfogadási feltételek (a Megértés lépésben rögzítve) | 1 |
| **Mérföldkő** | „A tárolási réteg kész” | tervező | mérföldkő-kapu: az eddigi összes teszt zöld | 2–6 |
| **Feladat** (`Task`) | „`src/repo.js`: CRUD a `todos` táblára” | tervező | a feladat saját gépi checkjei | 1–8 / mérföldkő |
| **Lépés** (`Step`) | „generáld a fájlt” → „futtasd a teszteket” → „javíts” | végrehajtó, futás közben | a lépés checkje | 1–4 / feladat |

A **feladat a tervezés atomja** (ennél kisebbet nem ütemezünk, ennél nagyobbat nem adunk a modellnek
egyben); a lépéseket a végrehajtó generálja ([02-terv-vegrehajtas-ellenorzes.md](02-terv-vegrehajtas-ellenorzes.md)).
Ami determinisztikusan megoldható (sablon másolása, teszt futtatása, repo-térkép), az **nem** LLM-hívás.

## 3. Adatszerkezet (TypeScript-vázlat)

```ts
type NodeId = string;                                   // "M2.F3"
type TaskKind = 'scaffold' | 'contract' | 'test' | 'code' | 'config' | 'doc' | 'research' | 'integrate';
type Status = 'pending' | 'ready' | 'running' | 'verifying' | 'done' | 'failed' | 'blocked';

interface Check {                                       // gépi "Kész, ha"
  kind: 'parse' | 'typecheck' | 'lint' | 'test' | 'red-test' | 'schema' | 'smoke' | 'guard' | 'critic';
  target: string; expect?: string;                      // pl. "test/repo.test.js", "6 passed, 0 failed"
}
interface Budget { maxAttempts: number; maxTokensOut: number; maxWallS: number }
interface Task {
  id: NodeId; milestone: NodeId; title: string; kind: TaskKind;   // title: 1 magyar mondat
  writes: string[];                                     // a fájlok, amiket CSAK ez a feladat ír (tulajdon)
  reads: string[];                                      // szerződés, függőségek aláírásai, tesztek
  dependsOn: NodeId[];                                  // a DAG élei
  accept: Check[];                                      // legalább egy nem-'critic' check kötelező
  budget: Budget; status: Status; attempts: number;
  recipe?: string;                                      // ha a kódtudástár egy receptjéből jön
}
interface Plan {
  goalId: string; version: number;                      // minden újratervezés +1
  acceptance: string[];                                 // a cél elfogadási feltételei (AC1…)
  contractsHash?: string;                               // a befagyasztott szerződésfájlok hash-e
  milestones: { id: NodeId; title: string; gate: Check[] }[];
  tasks: Task[]; createdBy: 'recipe' | 'recipe+model' | 'model';
}
```

## 4. A függőségi gráf (DAG) szabályai

1. **Körmentes.** Topologikus rendezés (Kahn); kör esetén a terv érvénytelen.
2. **Egy fájl — egy író.** Minden fájl pontosan egy feladat `writes` listájában szerepel; későbbi
   módosítás csak külön `edit` feladattal, ami az eredeti írótól függ ([03-tobbfajlos-projektek.md](03-tobbfajlos-projektek.md)).
3. **Olvasási zártság.** Amit egy feladat `reads`-ben kér, azt a sablon adja, vagy egy **ősének** a `writes`-a.
4. **Teszt a kód előtt, más kézből.** A `test` feladat a hozzá tartozó `code` feladat őse, és sosem
   ugyanaz a feladat írja a tesztet és a kódot (különben a modell a tesztet a saját hibájához igazítja).
5. **Sorrend egy sávra.** Egy Ollama-sáv van, tehát sorban fut: a „kész” halmazból a kritikus úton lévő
   feladat jön; döntetlennél a rövidebb (gyorsabb visszajelzés).

```python
def validate(plan) -> list[str]:
    errs, owners = [], {}
    for t in plan.tasks:
        for f in t.writes:
            if f in owners: errs.append(f"{f}: két író ({owners[f]}, {t.id})")
            owners[f] = t.id
        if not any(c.kind != "critic" for c in t.accept):
            errs.append(f"{t.id}: nincs gépi ellenőrzés")
    order = toposort(plan.tasks)                       # None, ha kör van
    if order is None:
        return errs + ["körkörös függőség"]
    for t in order:
        anc = ancestors(t, plan)                       # tranzitív dependsOn
        for r in t.reads:
            if r not in SCAFFOLD_FILES and owners.get(r) not in anc:
                errs.append(f"{t.id} olvassa: {r}, de az írója ({owners.get(r)}) nem őse")
    return errs
```

## 5. Méretezés: mikor elég kicsi egy feladat?

Egy feladat akkor mehet a modellhez, ha **mindegyik** sor teljesül. A határok kiinduló értékek
(**becslés**), a P0 mérései után hangoljuk ([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

| Szempont | Határ (becslés) | Ha nem teljesül |
|---|---|---|
| Kimenet | 1 fájl, ≤ ~80 sor (~800 token) | bontás függvényekre, egymás után ugyanabba a fájlba |
| Bemenő kontextus | ≤ ~2500 token | teljes fájl helyett aláírások (repo-térkép) |
| Ellenőrizhetőség | van legalább egy gépi check | előbb egy `test` feladat |
| Ismert API | a használt könyvtár szerepel a kódtudástárban vagy a receptben | előbb egy `research` feladat (dokumentáció-kivonat) |
| Döntésmentes | nem kell benne architektúra-döntés | a döntés a `contract` feladatba vagy a felhasználóhoz kerül |
| Idő | generálás ≤ ~5 perc a választott modellel | kisebb darabok |

Az ~5 perc indoklása: 800 token egy 7B-s kódoló modellel ~3 tok/s-mal (becslés) ~4,5 perc; a mért gemma4:e2b
sebességével ~2 perc. **Felső korlátok:** max 3 szint mély bontás; egy cél max ~12 feladat (P5 előtt) /
~30 (P5 után) — e fölött már projekt, és Auri megkérdezi, melyik részével kezdje. Szintekben: egy feladat
L1–L2 méretű, az egész cél L3–L4 ([../06-programozas/01-cel-es-szintek.md](../06-programozas/01-cel-es-szintek.md)).

**Bontási heurisztikák** (ebben a sorrendben): (1) rétegek alulról felfelé: szerződés/típusok →
tiszta logika → tárolás → HTTP/UI → összekötés → végponttól végpontig tartó teszt; (2) fájlonként;
(3) függvényenként, ha a fájl túl nagy; (4) előbb a „boldog út”, a szélső esetek külön feladatban,
saját tesztekkel; (5) a teszt mindig a kód előtt.

## 6. Szerződések először

Minden implementáció előtt egy `contract` feladat írja meg a **közös nyelvet**: adattípusok,
modulhatárok függvény-aláírásai, API-séma (útvonal, státuszkód, hibaforma). Ellenőrzése: `parse` +
Kritikus-átnézés (+ nyilvános API-nál a felhasználó jóváhagyása). Utána **befagyasztjuk**: a hash a
`plan.contractsHash`-be kerül, és a végrehajtó minden olyan kimenetet elutasít, ami hozzányúlna.
Változtatás csak `contract.change_request` eseménnyel, újratervezéssel. (Előkép: a `JARVIS_BUILD.md`
2.1-es `contracts.py`-ja, amit az AI-3 „szó szerint” elsőként hozott létre — [03-tobbfajlos-projektek.md](03-tobbfajlos-projektek.md).)

```js
// src/contract.js — az F2 feladat kimenete; BEFAGYASZTVA (hash a tervben)
/** @typedef {{ id: number, title: string, done: boolean, createdAt: string }} Todo */
export const ROUTES = {
  list: ['GET', '/todos'], get: ['GET', '/todos/:id'], create: ['POST', '/todos'],
  update: ['PATCH', '/todos/:id'], remove: ['DELETE', '/todos/:id'],
};
/** Minden 4xx válasz teste: { error: { code: string, message: string } } */
export const TITLE_MAX = 200;
```

Kis modellnél ez azért működik, mert minden későbbi prompt a rövid szerződést kapja (~300 token,
becslés) a többi fájl teljes szövege helyett → kevesebb kitalált név, egyező mezők.

## 7. Ki készíti a tervet?

Elsőként a **recept** (korábban sikeresen végigfutott terv-sablon a kódtudástárból, legalább T3 bizalommal,
0 LLM-hívás); ha nincs, a **Gondolkodó** szerep szigorú JSON-sémára (1–3 hívás, hibalistás javítással):

```python
def make_plan(goal, kb, llm) -> Plan:
    recipe = kb.best_recipe(goal, min_trust=3)          # T3+: bizonyított (06-programozas/03)
    plan = recipe.instantiate(goal) if recipe else llm.plan_json(goal, PLAN_SCHEMA, hints=kb.similar_plans(goal, k=2))
    for _ in range(3):
        errs = validate(plan) + size_violations(plan)
        if not errs:
            return critic_note(plan)          # Kritikus: egy kör, csak javaslat, nem kapu
        plan = llm.fix_plan(plan, errs)       # csak a hibalista megy vissza, nem az egész cél
    raise NeedsUser("Nem sikerült érvényes tervet készíteni.", plan, errs)
```

A sikeresen végigfutott terv **recept** lesz (entitásnév, mezők → paraméter), legközelebb LLM nélkül készül el — az egyik fő „okosodási” csatorna ([05](05-teljes-pelda.md) 9. pont).

## 8. A rossz bontás jelei

„Írd meg az egészet” check nélkül; két író egy fájlon; a szerződés a kód **után**; ugyanaz írja a tesztet
és a kódot; egy `research` eredménye egyetlen `reads`-ben sem szerepel (elveszett munka); túl apró
feladatok — ha közben szerepet is váltunk, az feladatonként mért ~6 s (e2b) / ~17 s (e4b) prefixváltás.

## 9. Kész, ha (a feladatbontó modulra)

- Az E5 készlet (5–8 többfájlos mini-projekt) céljaira a `validate()` 0 hibát ad, és minden feladat az 5. pont határain belül van.
- Szándékosan hibás tervet (kör, kétírós fájl, check nélküli feladat, ős nélküli olvasás) 100%-ban elutasít (egységtesztek).
- Receptből a terv LLM-hívás nélkül, < 1 s alatt elkészül; a terv JSON-ként verziózva a futási naplóba kerül.

## Kapcsolódó

- [02-terv-vegrehajtas-ellenorzes.md](02-terv-vegrehajtas-ellenorzes.md) · [03-tobbfajlos-projektek.md](03-tobbfajlos-projektek.md) · [05-teljes-pelda.md](05-teljes-pelda.md) · [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) (a Terv lépés)
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) (receptek) · [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) (teszt a kód előtt) · [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
