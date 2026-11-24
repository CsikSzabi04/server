# Router és ütemező

> **Miről szól:** hogyan dönti el Auri, melyik úton gondolkodjon — cache → fast-path → kis helyi
> modell → nagyobb helyi modell → (opcionális) felhő —, hogyan becsüli a nehézséget, mikor eszkalál,
> mekkora keretet ad, és hogyan osztja be az **egyetlen Ollama-sávot** élő és háttérmunka között.

## 1. Szintek

| Szint | Mi | Modell / eszköz | Idő (becslés, ha nem jelölt) | Mikor elég |
|---|---|---|---|---|
| **L0** cache | ellenőrzött válasz / kód szó szerinti vagy jelentés szerinti egyezéssel | — (+ `embeddinggemma`) | < 1 s | ismételt vagy nagyon hasonló kérdés |
| **L1** fast-path | determinisztikus felismerés és eszköz | Jarvis `fastpath.py` (mért 0,05 ms/mondat), számológép, „futtasd a tárolt teszteket” | < 1 s | parancs, számolás, ismert eszköz |
| **L2** kis helyi modell + RAG | a modell a visszakeresett tudásból fogalmaz / kódol | persona: gemma4:e2b; szerepkönyv: qwen3.5:4b (javaslat, ld. lent) | 400 token ≈ 65 s e2b-n (levezetés a mért 6,2 tok/s-ból) | a legtöbb kérdés és kis függvény |
| **L3** nagyobb helyi | nehezebb kód, Kritikus, Tanár | kódolómodell (ha telepítve, P6) vagy gemma4:e4b | percek | L2 bukott, vagy a becslés eleve nehéznek mondja |
| **L4** felhő | opcionális, alapból **ki** | Groq → Gemini, kitakarás után | gyors, de kvótás | csak a felhasználó engedélyével ([03-felhos-segitseg-opcionalis.md](03-felhos-segitseg-opcionalis.md)) |

Megfeleltetés a mai kóddal: az `arbiter.ts` `retrieval` útja → L0/L2 (RAG), a `local-model` → L2, a
`fallback` → L4; a `local-brain` (Markov) megszűnik. A `web/api/chat.ts` lánca (helyi → Groq → Gemini)
az L2 → L4 lépés mai, egyszerű formája.

### Munkamenet és modell szintenként

A belső szerepek (Kérdező, Gondolkodó, Tesztelő, Kritikus, Tanár) **egy modellen, egy rögzített
szerepkönyv-rendszerprompttal**, csak hozzáfűzve futnak; a felhasználónak szóló választ a
**Fogalmazó** a **persona-munkamenetben** írja ([../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md)).

| Mód / szint | Szerepkönyv-munkamenet (belső lépések) | Persona-munkamenet (Fogalmazó) |
|---|---|---|
| `chat`, L2 | **nincs** — a tudás egyenesen a `<kontextus>`-ba | gemma4:e2b |
| `code` / `research`, L2 | **javaslat:** qwen3.5:4b | gemma4:e2b |
| `code`, L3 | kódolómodell (P6) | gemma4:e2b |
| háttér (`study`) | a háttérmodell (qwen3.5:4b vagy a kódolómodell) | — (nincs felhasználó) |

Miért külön modellen a szerepkönyv? Ugyanazon a modellen a két munkamenet közti átlépés irányonként
egy előtag-újratöltés (gemma4:e2b-n a mért prefixváltás ~6 s), és a Jarvis meleg előtagja is
elveszne. A qwen3.5:4b munkameneten belüli első tokenje 2,99 s (mért) — egy perces kódgenerálás
mellett ez kicsi, a tok/s pedig az e2b-vel egyező (6,2). **Feltétel:** a P0 RAM-mérése szerint a két
modell együtt elfér (a qwen3.5:4b RAM-ja nem mért). Ha nem fér el, minden az e2b-n fut, és
kérésenként ~2 váltást fizetünk. Hogy a valóságban melyik gyorsabb: **mérni kell** (a szerepkönyv
rövidebb a Jarvis ~1400–1700 tokenes előtagjánál, a CPU-s prefill-sebesség pedig nem mért).

## 2. Nehézségbecslés

```python
def assess(goal: Goal, recall: Recall, stats: Stats) -> Assessment:
    if (hit := recall.verified_fresh()):
        return Assessment(level=0, ...)
    if fastpath.match(goal.text):
        return Assessment(level=1, ...)
    kind = classify(goal.text)                      # szabályok; bizonytalanban kis modell, JSON-séma
    known = recall.known_ratio                      # 0..1: a kulcsfogalmak ellenőrzött lefedettsége
    sim = stats.success_rate(kind, like=goal, default=0.5)   # hasonló epizódok sikeraránya
    size = min(estimate_out_tokens(goal) / 1500, 1.0)        # „függvény” < „osztály” < „projekt”
    d = 0.35 * (1 - known) + 0.35 * (1 - sim) + 0.2 * size + 0.1 * goal.freshness_risk
    level = 2 if d < 0.6 or not has_level(3) else 3          # súlyok és küszöb: becslés
    return Assessment(kind=kind, level=level, difficulty=d,
                      predicted_success=1 - d, budget=BUDGETS[kind].scaled(d), ...)
```

A súlyok kiinduló becslések. A P4-től az epizódokból kalibráljuk (pl. logisztikus regresszió a
sikerre); a `predicted_success` és a tényleges kimenet eltérése a **kalibráció** mérőszáma
([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

| Feladat | Tudástár | Hasonlók sikere | Induló szint | Megjegyzés |
|---|---|---|---|---|
| chat, tény | ellenőrzött, friss találat | — | L0 | forrással |
| chat, tény | nincs | — | L2 + web, ha engedélyezett | forrás nélkül: „nem ellenőriztem” jelzés |
| code, kis függvény | részleges | ≥ 0,7 | L2 | P0 |
| code, kis függvény | nincs | < 0,4 | L2, eszkaláció engedve | a felhasználó látja: „lehet, hogy tovább tart” |
| code, több fájl | — | — | terv L2-n, lépések L2/L3-on, háttérben | P5 |
| research | — | — | L2 + Web-szörföző | P2 |

## 3. Eszkalációs létra

| Kudarc | Következő lépés |
|---|---|
| VERIFY bukik 3 javítási kör után | L2 → L3, ha van és a keret engedi |
| Ugyanaz a hiba-aláírás kétszer | ne még egy kör: `ImportError` / `AttributeError` → dokumentáció a webről (P2); más → L3 |
| Hiányzó tudás (ismeretlen API, verzió) | Web-szörföző, a szint marad |
| L3 is bukik | L4, ha a felhasználó engedélyezte; különben GIVE_UP + hiánylista |
| Időtúllépés | ugyanaz a szint kisebb részfeladattal; a második után GIVE_UP |
| Ollama nem érhető el | élőben: a meglévő lánc (felhő, ha be van kapcsolva); háttérben: a job vár |

Háttérfeladat (önálló tanulás) **soha** nem eszkalál L4-re.

## 4. Az egy-sávos ütemező

| Elsőbbség | Ki | Megszakít | Megszakítható |
|---|---|---|---|
| `VOICE` | Jarvis hangkör (közvetlenül az Ollamát hívja, `POST /activity`-vel jelez) | minden háttérmunkát | nem |
| `CHAT` | AuriGPT élő kérés | `BACKGROUND` | nem |
| `TASK` | a felhasználó által indított hosszú feladat | `BACKGROUND` | nem, de **lépései között** élő kérés előre mehet |
| `BACKGROUND` | önálló tanulás, ismétlés, tesztek újrafuttatása | — | igen, azonnal (stream zárása + ellenőrzőpont) |

Szabályok:

1. **Bérlet modellhívásonként**, nem feladatonként → az élő kérés a hosszú feladat lépései közé fér.
2. **Háttérmunka csak tétlenségben:** ≥ 10 perce (becslés) nincs Jarvis-kör, AuriGPT-kérés és input
   (`GetLastInputInfo`), és ki van kapcsolva a „csend” kapcsoló (hangfelvétel alatt: `JARVIS_BUILD.md`).
3. **Modell- és munkamenet-affinitás:** azonos elsőbbségen belül előre az a kérés, amelyik a már
   betöltött modellt és ugyanazt a munkamenetet (szerepkönyv vagy persona) folytatja — kevesebb
   betöltés (hidegen 18,5–38,3 s, mért) és prefixváltás ([01-helyi-modellek.md](01-helyi-modellek.md), 4. pont).
4. **A Jarvist nem lassíthatja:** a Core nem tudja megszakítani a Jarvis hívását, csak kitér előle.
   Hogy két *különböző* betöltött modellnél az Ollama párhuzamosan futtat-e (és ez CPU-n mennyire
   lassít): **mérni kell** — addig a `VOICE` alatt a Core semmit nem indít.

```python
class OllamaGate:
    async def lease(self, prio: Priority, model: str) -> AsyncIterator[Lease]:
        async with self._cv:
            await self._cv.wait_for(lambda: self._can_run(prio, model))
            self._holder = lease = Lease(prio, model, cancel=asyncio.Event())
        try:
            yield lease                              # a hívó streamelés közben figyeli a lease.cancel-t
        finally:
            async with self._cv:
                self._holder = None
                self._cv.notify_all()

    def _can_run(self, prio: Priority, model: str) -> bool:
        if self._holder is not None or self.voice_active():
            return False
        if prio is Priority.BACKGROUND and (self.quiet_switch or self.idle_seconds() < 600):
            return False
        return self._best_waiting() == (prio, model)  # elsőbbség, majd modell-affinitás

    async def on_activity(self, source: str) -> None:  # POST /activity, AuriGPT-kérés, input
        self.last_active = time.monotonic()
        if self._holder and self._holder.prio is Priority.BACKGROUND:
            self._holder.cancel.set()                  # → a stream zárul, ellenőrzőpont, PAUSED
```

## 5. Keret szintenként (becslés, kalibrálandó)

| Szint | Max. hívás / lépés | Max. kimeneti token / hívás | Időkorlát / hívás |
|---|---|---|---|
| L2 élő | 1 | 400 (chat) / 1200 (kód) | 90 s / 240 s |
| L2 háttér | 1 | 1200 | 300 s |
| L3 | 1 | 1500 | 600 s (csak háttérben vagy a felhasználó tudtával) |
| L4 | 1 | a szolgáltató korlátja | 60 s |

A feladatszintű keretek (`chat` / `code` / `research` / `study`):
[../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md), 5. pont.

## 6. Kész, ha

- Minden modellhívás az `OllamaGate`-en át megy (teszt: közvetlen hívás nincs a Core-ban).
- Háttérmunka közben egy `POST /activity` után a stream ≤ 1 s-on belül zárul (cél, mérni kell).
- Élő `CHAT`-kérés egy futó `TASK` mellett legfeljebb egy lépésnyit vár (mérve az epizódnaplóból).
- Az L0/L1/L2/L3/L4 arányok és a szintenkénti siker a statisztikában látszanak (`GET /stats`).

## Kapcsolódó

- [01-helyi-modellek.md](01-helyi-modellek.md) — melyik modell melyik szinten
- [03-felhos-segitseg-opcionalis.md](03-felhos-segitseg-opcionalis.md) — L4 · [04-cache-es-ujrahasznositas.md](04-cache-es-ujrahasznositas.md) — L0
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) — szerepkönyv, Fogalmazó
- [../00-alapok/01-mit-jelent-gondolkodni.md](../00-alapok/01-mit-jelent-gondolkodni.md) — metakogníció
- [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) — megszakítás, keretek
- [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) — `POST /activity`
- [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) — háttérmunka
