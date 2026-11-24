# Architektúra — áttekintés

> **Miről szól:** a gondolkodó agy alkotórészei (Memória/Tudástár, Router, Gondolkodók, Web-szörföző,
> Ellenőrző/Sandbox, Ütemező, Tananyag-kezelő), mindegyik felelőssége és határa, a köztük lévő
> interfészek vázlata, és hogy melyik meglévő kódra épülnek.

## 1. Az alapgondolat

A BRAIN szerepe: **memória + irányító + ellenőrző**. A mondatokat és a kódot a **modell** fogalmazza;
az agy dönti el, *mit* kérdezzen tőle, *mivel* egészítse ki, és *ellenőrzi*, amit kapott. A mai
böngészős „saját válasz” (kulcsszó + Markov) nem fejlődik tovább — a tudásbázis és a seedek
átkerülnek a tudástárba ([03-hol-fut-auri-core.md](03-hol-fut-auri-core.md), migráció).

## 2. Komponensdiagram

```
          AuriGPT (web, böngésző)                  Jarvis (hangos daemon, :8790)
                   │ REST + SSE                               │ REST + SSE
┌──────────────────▼──────────────────────────────────────────▼──────────────────────┐
│ AURI CORE  (helyi Python-szolgáltatás, 127.0.0.1:8791 — javaslat)                   │
│                                                                                     │
│  API-réteg ──▶ Adatvédelmi kapu ──▶ CIKLUSVEZÉRLŐ (a gondolkodó ciklus, epizódnapló) │
│                                          │                                          │
│     ┌──────────────┬─────────────────────┼──────────────────┬───────────────────┐   │
│     ▼              ▼                     ▼                  ▼                   ▼   │
│  MEMÓRIA /      ROUTER               GONDOLKODÓK        WEB-SZÖRFÖZŐ       ELLENŐRZŐ /│
│  TUDÁSTÁR       szint, modell,       szerepek,          keres, olvas,      SANDBOX    │
│  SQLite+FTS5    keret, eszkaláció    prompt-sablonok    bizalom            tesztek    │
│  + vektorok          │                    │                  │                       │
│     ▲                └──────────▶  ÜTEMEZŐ (egy Ollama-sáv, elsőbbség, tétlenség) ◀─┘
│     │                                     ▲                                          │
│  TANANYAG-KEZELŐ ── háttér-jobok ─────────┘                                          │
└──────────────────────────────────────────┼──────────────────────────────────────────┘
                                           ▼
                   Ollama 127.0.0.1:11434        (opcionális: Groq / Gemini — csak kitakarás után)
```

Szabály: **minden** modellhívás (helyi és felhős) az Ütemezőn megy át, és **minden** írás a
tudástárba az Adatvédelmi kapun. Kivétel nincs — ez a két pont tartja a rendszert biztonságosnak és a
gépet használhatónak.

## 3. Felelősségek

| Komponens | Felelős ezért | **Nem** felelős ezért | Meglévő kód, amire épül | Fázis |
|---|---|---|---|---|
| **Memória / Tudástár** | tudáselemek, kódrészletek + tesztek, források, epizódok, tanulságok tárolása; hibrid keresés (FTS5 + vektor); eredet; státusz | annak eldöntése, hogy valami igaz-e (azt az Ellenőrző mondja) | `web/src/brain/seed/*`, `webStore.ts`; Jarvis `memory/store.py` (SQLite WAL + FTS5), `memory/embed.py` | P1 |
| **Router** | nehézségbecslés, induló szint (L0–L4), modell, keret, eszkaláció kudarc után | a modellhívás végrehajtása, sorban állás | `web/src/brain/arbiter.ts` (`decideRoute`), `web/api/chat.ts` lánc, Jarvis `mind/fastpath.py` | P0 (egyszerű) → P1 |
| **Gondolkodók** | belső szerepek egy szerepkönyv-munkamenetben (csak hozzáfűzés, JSON-kimenet); a válasz a **Fogalmazó**val a persona-munkamenetben; streaming | hogy a kimenet igaz-e; hogy mikor fut | Jarvis `mind/ollama_provider.py`, `prompts.py`, `agent.py` | P0 → P3 (szerepek) |
| **Web-szörföző** | keresés, oldal letöltése és tisztítása, lényegkivonás, forrás-bizalom | a tartalom végrehajtása (az adat, nem utasítás) | `web/api/search.ts`, `web/src/autolearn/*`, `web/src/brain/web.ts` | P2 |
| **Ellenőrző / Sandbox** | kód futtatása elszigetelten (időkorlát, temp mappa, hálózat nélkül), teszteredmény; tények egyeztetése | a kód megírása, a javítás | Jarvis hallucináció-őr (`agent.py`) mint minta; a sandbox **új** | P0 |
| **Ütemező** | az egyetlen Ollama-sáv kiosztása, elsőbbségi osztályok, tétlenség-figyelés, megszakítás, háttér-jobok | hogy *mit* gondoljon a rendszer | `JARVIS_BUILD.md` koordinációs szabály; `selfStudy.ts` rate limit | P0 (zár) → P1 |
| **Tananyag-kezelő** | témák és gyakorlófeladatok sorrendje, hiánylista, ismétlési időpontok | a tanulás végrehajtása (az a ciklus) | `web/src/brain/selfStudy.ts` (`STUDY_SEEDS`) | P4 |
| **Ciklusvezérlő** | a ciklus lépései, keret-figyelés, megállás, ellenőrzőpont, epizódnapló | modellválasztás (Router), tárolás (Memória) | Jarvis `agent.py` (max. 3 kör) mint minta | P0 |
| **Adatvédelmi kapu** | személyes adat és titok kiszűrése írás és kimenő hívás előtt | jogosultság (az API-réteg dönti el a szintet) | `web/src/brain/privacy.ts` (`isPersonal`), Jarvis `memory/redact.py` | P0 |

## 4. Interfészek (vázlat, Python)

```python
class KnowledgeStore(Protocol):
    async def search(self, q: str, *, kinds: set[str], scope: Scope, k: int = 8) -> list[Hit]: ...
    async def put(self, item: Item, prov: list[Provenance]) -> str: ...      # alapból status='hypothesis'
    async def promote(self, item_id: str, v: Verification) -> None: ...     # → 'verified'
    async def demote(self, item_id: str, reason: str) -> None: ...          # → 'stale' / 'refuted'
    async def record_episode(self, ep: Episode) -> None: ...

class Router(Protocol):
    def assess(self, goal: Goal, recall: list[Hit], history: Stats) -> Assessment: ...
    def escalate(self, level: int, failure: Failure) -> int | None: ...    # None = nincs feljebb

class Thinker(Protocol):
    async def run(self, role: Role, inp: PromptInput, *, model: str,
                  schema: dict | None, max_tokens: int) -> ThinkerOutput: ...

class WebSurfer(Protocol):
    async def research(self, question: str, *, max_searches: int, max_pages: int) -> list[Evidence]: ...

class Verifier(Protocol):
    async def run_tests(self, files: dict[str, str], tests: dict[str, str], lang: str,
                        timeout_s: float) -> TestReport: ...
    async def check_claim(self, claim: str, evidence: list[Evidence]) -> ClaimVerdict: ...

class Scheduler(Protocol):
    def lease(self, prio: Priority, model: str) -> AbstractAsyncContextManager[Lease]: ...
    def user_active(self) -> bool: ...

class Curriculum(Protocol):
    def next_jobs(self, now: datetime, limit: int) -> list[StudyJob]: ...
    def report(self, job_id: str, outcome: Outcome) -> None: ...
```

A komponensek **csak** ezeken át beszélnek; így mindegyik külön tesztelhető mockkal (ahogy a Jarvis
`fakes.py` teszi), és Ollama nélkül is fut a tesztcsomag.

## 5. Egy kérés útja röviden

1. API-réteg: azonosítás (vendég / bejelentkezett), keret a módhoz (`chat` / `code` / `research`).
2. Ciklusvezérlő → Memória: **emlékezés** (cache + tudástár). Ellenőrzött, friss találat → válasz.
3. Router: `assess()` → induló szint, modell, keret.
4. Gondolkodók (az Ütemező bérletével): megértés, terv, cselekvés. Kell web? → Web-szörföző.
5. Ellenőrző: tesztek / források. Hiba → javítás (≤ 3 kör) vagy `escalate()`.
6. Ciklusvezérlő: tanulság → Adatvédelmi kapu → Memória (eredettel, státusszal) + epizódnapló.

Részletesen: [02-gondolkodo-ciklus.md](02-gondolkodo-ciklus.md).

## 6. Tervezési döntések (röviden indokolva)

| Döntés | Miért |
|---|---|
| **Python** az Auri Core nyelve | a Jarvis Mind (Ollama-kliens, eszköz-regiszter, memória, kitakarás) Pythonban kész és tesztelt; a sandbox-folyamatkezelés és az SQLite FTS5 a standard könyvtárban van |
| **SQLite** (WAL + FTS5) egy fájlban | helyi, nulla üzemeltetés, a Jarvis már így tárol; a vektoros keresés eleinte numpy-val ([04-tarolas-es-adatfolyam.md](04-tarolas-es-adatfolyam.md)) |
| **Strukturált kimenet** minden belső lépésnél | a kis modellek szabad szövegét nehéz feldolgozni; JSON-séma + validálás olcsó |
| **Egy szerepkönyv**, csak hozzáfűzés; a Fogalmazó a persona-munkamenetben | a mért KV-cache viselkedés miatt ([../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md)) |
| **Egy nyelvfelismerő** a Core-ban | ma kettő van (`web/src/autolearn/lang.ts`, `web/src/brain/lang.ts` — mindkettőben `detectLang`); eltérő eredmény eltérő utat adna |
| **Minden lépés naplózva** (epizód) | ebből tanul a router, ebből mérünk, ebből lesz a tanulság |

## 7. Kész, ha (P1 — az architektúra szintjén)

- Mind a 7 komponens + a ciklusvezérlő a fenti interfész mögött van, mockkal tesztelve.
- Egy `code` kérés a teljes úton végigmegy, és egy epizód + (siker esetén) egy `verified` kódrészlet
  keletkezik eredettel.
- Nincs olyan kódút, ami az Ütemezőt vagy az Adatvédelmi kaput megkerüli (teszt ellenőrzi).

## Kapcsolódó

- [02-gondolkodo-ciklus.md](02-gondolkodo-ciklus.md) — a ciklus állapotai és keretei
- [03-hol-fut-auri-core.md](03-hol-fut-auri-core.md) — folyamatmodell, API, migráció
- [04-tarolas-es-adatfolyam.md](04-tarolas-es-adatfolyam.md) — séma és adatfolyam
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) — a Gondolkodók szerepei
- [../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md) — a Web-szörföző
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) — az Ellenőrző/Sandbox
- [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) — a Tananyag-kezelő munkája
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — Router + Ütemező
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) — az Adatvédelmi kapu szabályai
