# Éjszakai önálló tanulás — ütemező, ami mindig enged a felhasználónak

> **Miről szól:** hogyan tanul az agy magától, amikor a gép szabad: hogyan érzékeli a tétlenséget,
> mennyi CPU-t használhat, hogyan osztozik az egyetlen Ollama-sávon, honnan veszi a témákat, hogyan
> áll meg azonnal, ha a felhasználó visszajön, és mit jelent reggel. Fázis: **P4**.

## 1. Keret és a mai állapot

- CPU-only gép, **egy Ollama-sáv** (`OLLAMA_NUM_PARALLEL=1`): a tanulás és a felhasználó ugyanazért
  a sávért versenyez. A `JARVIS_BUILD.md` naplójában rögzített eset: amikor egy eval és egy smoke-teszt
  ugyanazon az Ollamán futott, a Jarvis első válaszai a terheletlen állapot többszörösére lassultak.
  → **Szabály: a felhasználó mindig nyer; a tanulás kis, megszakítható egységekből áll.**
- A mai hurok (`web/src/brain-bridge/brainChat.ts`, `auri.brain.selfStudy`, alapból KI) 90 mp-enként
  kérdez, legfeljebb 40-szer munkamenetenként. Három hibája: **nem figyeli a tétlenséget**; a
  `/api/chat` láncán megy (Ollama → Groq → Gemini), tehát Ollama nélkül **felhős kvótát** fogyaszthat;
  és a választ ellenőrzés nélkül lepárolja. Az új ütemező mindhármat javítja.

## 2. Mikor szabad a gép? (tétlenség-érzékelés)

| Jel | Forrás | „Nem tétlen”, ha |
|---|---|---|
| Billentyű / egér | Windows `GetLastInputInfo` (user32, Pythonból `ctypes`) | az utolsó bemenet a küszöbön belül volt |
| Jarvis állapota | a Jarvis busz `state` eseménye | nem `idle` (listening, transcribing, thinking, speaking, acting) |
| AuriGPT / Core API | az Auri Core kéréssora | van futó vagy váró felhasználói kérés |
| Ollama | saját kérés-számláló + `/api/ps` | felhasználói kérés fut vagy vár |
| Más terhelés | CPU-kihasználtság (pl. `psutil`) | a tanulás nélkül is > 50% (becslés) |
| Teljes képernyő | előtérablak állapota | játék, videó, prezentáció fut |
| Kézi tiltás, mérés-zár | „Ma ne tanulj” kapcsoló; eval/bench jelzés | be van kapcsolva |

Küszöbök (kiinduló, **becslés**): az éjszakai ablakban (alap 01:00–06:00, állítható) **10 perc**
tétlenség (a Jarvis álom-fázis mintájára); napközben **20 perc**, és akkor csak „könnyű” munka.
Ha a gép éjjel ki van kapcsolva, a tanulás csak a napközbeni tétlen ablakokban fut.

## 3. Állapotgép

```
 OFF ──(bekapcsolva)──▶ WAITING ──(tétlen ≥ küszöb és van keret)──▶ STUDYING
  ▲                        ▲                                          │ felhasználói jel
  │                    COOLDOWN ◀──(5 perc csend)── PAUSED ◀── PAUSING ◀┘
  └──────────(kikapcsolás · keret elfogyott · 3 egymás utáni hiba)──────────
```

- **PAUSING:** a futó Ollama-kérés azonnal megszakad (`AbortController`, a stream lezárása), a
  sandbox-folyamat a teljes folyamatfájával együtt leáll, az egység állapota checkpointba kerül.
- **PAUSED → COOLDOWN:** a felhasználó elment, de 5 percig még nem indulunk újra (ne pattogjon).
- Cél: jeltől a megszakításig **≤ 1 s**. Hogy utána mennyi idő alatt szabadul fel ténylegesen az
  Ollama-sáv, **mérni kell** (modellenként és kérésmérettől függően eltérhet).

## 4. Erőforrás-keret

| Keret | Kiinduló érték (becslés) | Miért |
|---|---|---|
| Egy egység max. hossza | 3 perc, `num_predict` ≤ 512 | gyors megszakíthatóság |
| Szálak | `num_thread` 6 (a 12-ből) | a gép reagáljon; **mérni kell**, okoz-e modell-újratöltést |
| Munkaciklus | 25 perc munka / 5 perc szünet | hő és zaj; hőmérséklet csak külső eszközzel olvasható (opcionális) |
| Éjszakai keret | 4 óra munka · 200 modellhívás · 100 webkérés | kiszámítható terhelés |
| Felhő | **0** alapból | „helyi először”; csak külön, kifejezett engedéllyel |
| Sandbox | egyszerre 1 futás | CPU és biztonság ([../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md)) |
| Napközbeni „könnyű” munka | sandbox-újrafuttatás, deduplikálás, konszolidáció modell nélkül | nem foglalja az Ollamát |

**Modellválasztás és visszatérés.** Éjjel jöhet a nagyobb kódmodell (ha lesz). Napközben csak a
`gemma4:e2b` vagy semmi: ha a tanulás más modellt használ, a felhasználó visszatérésekor a Jarvis
modelljét vissza kell tölteni és a prefixét újramelegíteni (a prefixváltás mért ára `gemma4:e2b`-n
~6 s). Ezért PAUSING után az ütemező **azonnal kéri a Jarvis-prefix újramelegítését**, a
tanulómodellt pedig `keep_alive: 0`-val engedi el.

## 5. A témasor — mit tanuljon?

```ts
interface StudyItem {
  id: string;
  kind: 'failure' | 'gap' | 'review' | 'verify-hypothesis' | 'curriculum';
  topic: string;        // pl. 'python/asyncio/gather' — általános téma, soha nem a kérdés szövege
  reason: string;       // pl. "3× kellett hozzá web ezen a héten"
  priority: number;
  attempts: number;     // 3 sikertelen kör után félreteszi és jelenti
  notBefore?: string;   // ismétlésnél: esedékesség (ISO)
}
```

| Forrás | Hogyan kerül be | Súly (becslés) |
|---|---|---|
| Kudarc | elbukott sandbox-feladat; felhasználói javítás („nem, ez rossz”) | 3,0 |
| Hiány | a kérdés webre vagy modellhez ment, mert az agy nem fedte le | 2,0 |
| Esedékes ismétlés | a spaced repetition ütemezője ([03-ismetles-felejtes-konszolidacio.md](03-ismetles-felejtes-konszolidacio.md)) | 1,5 |
| Karantén | ellenőrzésre váró jelölt ([04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)) | 1,2 |
| Tananyag | a következő lecke ([../06-programozas/02-tananyag.md](../06-programozas/02-tananyag.md)) | 1,0 |

`priority = súly × (1 + 0,2 × előfordulás_az_elmúlt_7_napban) − 0,5 × [az elmúlt 24 órában már tanulta]`

A sorba kerülés előtt minden téma átmegy az `isPersonal` + `containsSecret` kapun. Kiértékelő
(held-out) feladat soha nem lehet téma ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)).

## 6. Egy tanulási egység

```python
async def run_unit(item: StudyItem, budget: Budget, gate: YieldGate) -> UnitResult:
    plan = make_plan(item)                    # pl. kérdés → kódpélda → teszt → futtatás → tanulság
    for step in plan.steps:
        if gate.should_yield() or budget.exhausted():
            return checkpoint(item, step)     # PAUSING: innen folytatható
        out = await step.run(abort=gate.signal, num_predict=512, model=budget.model)
        budget.charge(step, out)
        if step.is_check and not out.ok:
            return record_failure(item, out)  # a kudarc is jelölt (error-fix)
    return submit_candidates(plan.outputs)    # → canLearn → karantén → ellenőrzés
```

## 7. Napi tanulási jelentés

Reggel rövid jelentés (AuriGPT-ben és a HUD-on), személyes adat nélkül. Minta (a számok fiktívek):

```markdown
## Önálló tanulás — 2026-11-22 éjjel
- Idő: 3 ó 10 p munka (keret: 4 ó) · megszakítás: 2× (leglassabb: … ms)
- Egységek: 41 (kész 33 · félbehagyva 5 · elbukott 3)
- Jelöltek: 27 → ellenőrzött 12 · karantén 11 · elvetett 4 · kapu tiltotta 0
- Ismétlés: 18 esedékes → 15 rendben · 3 elbukott (→ vitatott)
- Legfontosabb tanulság: „…” (bizonyíték: sandbox-futás #…)
- Holnapi sor eleje: python/asyncio (kudarc) · react/useEffect (hiány)
- Felhő: 0 hívás · web: 37 kérés
```

## Kész, ha

- a tanulás csak tétlenségben indul, és felhasználói jelre ≤ 1 s alatt megszakad (20 próbán mérve);
- tanulás közben a felhasználó első kérésének késése nem nő érdemben a terheletlenhez képest
  (módszer: [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md));
- felhőhívás alapból 0, a keret túllépése teszttel bizonyítottan lehetetlen;
- minden tanulós éjszaka után van jelentés, és a félbehagyott egység másnap folytatható.

## Kapcsolódó

- [01-tanulasi-forrasok.md](01-tanulasi-forrasok.md) · [03-ismetles-felejtes-konszolidacio.md](03-ismetles-felejtes-konszolidacio.md) · [04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)
- [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) · [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md)
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
- [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) (P4)
