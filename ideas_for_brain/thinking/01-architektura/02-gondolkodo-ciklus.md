# A gondolkodó ciklus részletesen

> **Miről szól:** a ciklus állapotgépe (emlékezés → megértés → terv → cselekvés → ellenőrzés →
> javítás → tanulság → megjegyzés), lépésenként a be- és kimenetekkel és a szerepekkel, a két
> munkamenet (szerepkönyv / persona), a megállási feltételek, a keretek, a megszakítás és a pszeudokód.

## 1. Állapotok

```
RECALL ──(ellenőrzött, friss találat)─────────────────────────────────────────▶ DONE
  │ nincs / részleges
  ▼
UNDERSTAND ──(kétértelmű + interaktív)──▶ ASK_USER
  ▼
PLAN ──▶ ACT ──▶ VERIFY ──ok──▶ REFLECT ──▶ STORE ──▶ DONE
                   │ hiba
                   ▼
                 REPAIR ──(kör ≤ 3, van haladás, van keret)──▶ VERIFY
                   │ nem
                   ├──(Router: van erősebb szint)──▶ PLAN (eszkalált szinten)
                   └──▶ REFLECT (kudarc-tanulság) ──▶ STORE (hipotézisként) ──▶ GIVE_UP
Bármely lépés között:  felhasználó aktív (háttérfeladat) → PAUSED  ·  lemondás → CANCELLED
```

Kódban: `State = RECALL | UNDERSTAND | PLAN | ACT | VERIFY | REPAIR | REFLECT | STORE`, végállapotok:
`DONE | ASK_USER | GIVE_UP | PAUSED | CANCELLED`. Élő kérésnél a DONE / GIVE_UP után a **Fogalmazó**
mondja el az eredményt a felhasználónak (3. pont) — ez kimeneti lépés, nem a ciklus állapota.

## 2. Lépésenként

| Lépés | Bemenet | Kimenet | Ki végzi (szerep) | Költség (becslés) | Hiba esetén |
|---|---|---|---|---|---|
| **RECALL** emlékezés | `Goal` (szöveg, mód, scope) | `Recall`: találatok bizalommal, cache-jelölt, hasonló epizódok, tanulságok | Memória (modell nélkül) | < 1 s (FTS + 1 beágyazás) | üres → UNDERSTAND |
| **UNDERSTAND** megértés | `Goal` + `Recall` | `Spec` (mit kérnek, be/ki, korlátok, nyitott kérdés) + `Assessment` | **Kérdező** (JSON) + Router | 1 hívás, ~100–200 token | kétértelmű → ASK_USER (élő) / kimondott alapértelmezés (háttér) |
| **PLAN** terv | `Spec` + `Recall` | `Plan`: lépések, mindegyikhez `check`; kódnál a tesztek | P0: sablonterv + **Tesztelő** (tesztek a kód előtt); P5: **Gondolkodó** tervez | 1–2 hívás | érvénytelen JSON → 1 újrapróba, majd sablon |
| **ACT** cselekvés | terv-lépés + találatok + tanulságok | `Artifact`: kód / válaszvázlat / kutatási jegyzet | **Gondolkodó**; web: Web-szörföző + **Kivonatoló** | 200–1500 token → ~30 s – 4 perc e2b-n (levezetés a mért 6,2 tok/s-ból) | időtúllépés → 1 újrapróba, majd eszkaláció |
| **VERIFY** ellenőrzés | `Artifact` + `Spec` | `Verdict`: ok / hiba, hiba-aláírás | Sandbox (determinisztikus); P3-tól **Kritikus** a sandbox eredményével; a döntés szabályalapú kód | 1–30 s + kritika | a sandbox hibázik (nem a kód) → GIVE_UP „infrastruktúra” |
| **REPAIR** javítás | `Artifact` + `Verdict` + korábbi aláírások | új `Artifact` (teljes fájl) | **Gondolkodó** | rövidebb, mint ACT | ld. 4. pont |
| **REFLECT** tanulság | az epizód lépései | `Lesson` (≤ 3 mondat, címkék) | **Tanár** vagy sablon | ~10–20 s | keret híján sablon-tanulság |
| **STORE** megjegyzés | `Artifact`, `Verdict`, `Lesson`, eredet | tudástár-sorok + epizód | Adatvédelmi kapu → Memória | < 1 s | a kapu elutasít → csak anonim statisztika |

A **teszt a javítás alatt zárolt**: a REPAIR csak a megoldást módosíthatja, a teszteket nem.

## 3. Két munkamenet: szerepkönyv és persona

- **Belső lépések** (UNDERSTAND … REFLECT): **egy modell, egy rögzített szerepkönyv-rendszerprompt**;
  a szerep a felhasználói üzenet elején áll (`<szerep>KRITIKUS</szerep>…`), a munkamenet **csak
  hozzáfűzéssel** nő → a lépések között nincs prefixváltás (gemma4:e2b-n a mért váltás ~6 s lenne).
- **A felhasználónak szóló válasz** (**Fogalmazó**) a **persona-munkamenetben** fut (Jarvis / AuriGPT
  persona-előtag); a belső eredmény a `<kontextus>` blokkba kerül, így ott sincs prefixváltás.
- Ha a két munkamenet **ugyanazon a modellen** fut, a kettő közti átlépés irányonként egy
  előtag-újratöltés. Ezért az élő `chat` csak a persona-munkamenetet használja (tudás a
  `<kontextus>`-ba, szerepkönyv nélkül), a `code` / `research` szerepkönyve pedig — ha a RAM engedi —
  másik modellen fut ([../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md)).

## 4. Megállási feltételek

| Feltétel | Végállapot | Megjegyzés |
|---|---|---|
| Ellenőrzött, friss találat a RECALL-ban | DONE | modellhívás nélkül |
| VERIFY sikeres | DONE | `verified` elem eredettel |
| 3 javítási kör után is hiba, és nincs erősebb szint | GIVE_UP | kudarc-tanulság + a téma a hiánylistára ([../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)) |
| Ugyanaz a hiba-aláírás kétszer egymás után | eszkaláció vagy GIVE_UP | nincs haladás — nem pazaroljuk a kört |
| Elfogyott a keret (idő / token / hívás) | GIVE_UP, részeredménnyel | a részeredmény legfeljebb `hypothesis` |
| Kétértelmű kérés, élő módban | ASK_USER | **egy** rövid kérdés |
| A felhasználó aktív lett (csak háttérfeladat) | PAUSED | ellenőrzőpontból folytatható |
| Lemondás vagy azonosságváltás | CANCELLED | a vendég-állapot eldobva (mint a Jarvisban) |
| Biztonsági szabály sérülne (hálózat, projektfájl, titok) | GIVE_UP („ezt nem teszem”) | [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md) |

## 5. Költségkeretek

`Budget(llm_calls, out_tokens, wall_s, repair_rounds=3, sandbox_runs=4, web_searches=0, web_pages=0,
escalations=1)` — az összes szerep hívásai együtt számítanak bele.

| Mód | LLM-hívás | Kimeneti token | Falióra | Javítás | Web (keresés / oldal) | Eszkaláció |
|---|---|---|---|---|---|---|
| `chat` (élő) | 2 | 400 | 90 s | 0 | 0 (1 / 2, ha engedélyezett) | 0 |
| `code` (élő, P0) | 8 | 5000 | 15 perc | 3 | 0 | 1 |
| `research` (P2) | 6 | 2500 | 10 perc | — | 3 / 6 | 1 |
| `study` (háttér, P4) | 10 | 8000 | 30 perc, szakaszosan | 3 | 3 / 6 | 0 (csak helyi) |

Minden szám **becslés** (pl. 5000 token a mért 6,2 tok/s-mal ~13,5 perc e2b-n); a P0 epizódjaiból
kalibráljuk. Eszkalációkor a **maradék** keret legfeljebb fele mehet az új szintre.

## 6. Pszeudokód

```python
async def run(goal: Goal, budget: Budget, level: int) -> Outcome:
    ep = Episode.start(goal, budget)
    recall = await memory.recall(goal)                                  # 1. EMLÉKEZÉS
    if (hit := recall.verified_fresh()) is not None:
        return ep.finish(DONE, answer=hit)
    spec = await understand(goal, recall, ep)                           # 2. MEGÉRTÉS (Kérdező)
    if spec.ambiguous and goal.interactive:
        return ep.finish(ASK_USER, question=spec.question)
    if spec.ambiguous:
        spec = spec.with_defaults()                                     # háttérben: kimondott feltevés
    while True:
        plan = await make_plan(spec, recall, level, ep)                 # 3. TERV (+ Tesztelő)
        artifact = await act(plan, recall, level, ep)                   # 4. CSELEKVÉS (Gondolkodó)
        seen: list[str] = []
        for rnd in range(budget.repair_rounds + 1):
            verdict = await verify(artifact, spec, ep)                  # 5. ELLENŐRZÉS
            if verdict.ok or (seen and verdict.signature == seen[-1]):
                break                                                   # siker / nincs haladás
            seen.append(verdict.signature)
            if rnd == budget.repair_rounds or ep.over_budget():
                break
            artifact = await repair(artifact, verdict, seen, level, ep) # 6. JAVÍTÁS
        if verdict.ok:
            break
        nxt = router.escalate(level, verdict.failure)
        if nxt is None or ep.escalations >= budget.escalations or ep.over_budget():
            await store(ep, artifact, verdict, await reflect(ep, ok=False))  # 7–8., hipotézisként
            return ep.finish(GIVE_UP, partial=artifact)
        level, ep.escalations = nxt, ep.escalations + 1
    await store(ep, artifact, verdict, await reflect(ep, ok=True))      # 7–8., verified + eredet
    return ep.finish(DONE, answer=artifact)                            # élőben utána: Fogalmazó
```

Minden modellhívás `async with scheduler.lease(prio, model):` alatt fut, és minden lépés előtt
`await ep.checkpoint()` fut — háttérfeladatnál ez dobja a `Paused` kivételt.

## 7. Megszakítás, folytatás, kérésre vs. magától

- Háttérfeladatnál, ha a felhasználó aktív lett, a futó stream **azonnal zárul** (a Jarvisban
  megfigyelt viselkedés: lezárt stream után az Ollama abbahagyja a generálást); a félkész kimenet eldobódik.
- Ellenőrzőpont a `jobs.checkpoint` mezőbe: utolsó **befejezett** lépés, `Spec`, `Plan`, `Artifact`,
  hiba-aláírások, elhasznált keret. Folytatás mindig lépéshatártól.
- **Kérésre** (élő): a felhasználó indítja, egy pontosító kérdés megengedett, nem szakad meg (csak
  lemondással), felhő csak engedéllyel. **Magától** (háttér, P4): a Tananyag-kezelő indítja
  tétlenségben, kimondott alapértelmezéssel dolgozik, bármikor megszakítható, felhő **soha**.

Epizódnapló-részlet (kitalált példa, nem mérés):

```json
{"id": "ep_0007", "mode": "code", "level_start": 2, "outcome": "DONE", "steps": [
  {"state": "RECALL", "verified_hit": false}, {"state": "UNDERSTAND", "role": "KERDEZO", "out_tokens": 140},
  {"state": "PLAN", "role": "TESZTELO", "tests": 5}, {"state": "ACT", "role": "GONDOLKODO", "out_tokens": 260},
  {"state": "VERIFY", "tests": "4/5", "signature": "AssertionError@test_spaces"},
  {"state": "REPAIR", "round": 1}, {"state": "VERIFY", "tests": "5/5"},
  {"state": "REFLECT", "lesson": "les_0042"}, {"state": "STORE", "items": ["snip_0131"], "status": "verified"}]}
```

## 8. Kész, ha

- Minden átmenetet mockolt teszt fed le; a 3. javítási kör után, ill. azonos hiba-aláírás kétszer → megáll.
- Egy `code` epizódon belül a szerepkönyv-munkamenetben 0 a prefixváltás (`LLMStats.prompt_ms`-ből mérve).
- Háttérfeladat felhasználói aktivitásra elengedi a sávot (cél: ≤ 1 s, mérni kell), és
  ellenőrzőpontból ugyanazzal az eredménnyel folytatható.
- Minden futásból epizód lesz; sikerből `verified` elem eredettel, kudarcból tanulság.

## Kapcsolódó

- [01-attekintes.md](01-attekintes.md) — a komponensek · [04-tarolas-es-adatfolyam.md](04-tarolas-es-adatfolyam.md) — `episodes`, `jobs`, `lessons`
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) — szerepek, szerepkönyv
- [../02-belso-parbeszed/02-vita-protokoll.md](../02-belso-parbeszed/02-vita-protokoll.md) — a VERIFY Kritikus-ága (P3)
- [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) — zárolt tesztek · [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md) — hiba-aláírás
- [../07-komplex-feladatok/02-terv-vegrehajtas-ellenorzes.md](../07-komplex-feladatok/02-terv-vegrehajtas-ellenorzes.md) — többlépéses terv
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — szintek, eszkaláció, Ütemező
