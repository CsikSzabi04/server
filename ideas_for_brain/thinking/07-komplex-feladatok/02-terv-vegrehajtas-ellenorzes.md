# Terv – végrehajtás – ellenőrzés: a komplex feladat motorja

> **Miről szól:** hogyan hajtja végre Auri a tervet feladatról feladatra: állapotgép, olcsótól drágáig
> haladó ellenőrzés, ellenőrzőpontok (checkpoint), visszagörgetés, újratervezés és költségvetések —
> egy CPU-s gépen, egyetlen Ollama-sávval, ahol bármelyik lépés elakadhat.

## 1. A ciklus egy képen

```
 TERV ─▶ következő kész feladat ─▶ VÉGREHAJTÁS ─▶ ELLENŐRZÉS (olcsó → drága)
  ▲                                                  │ ok                  │ hiba
  │                                                  ▼                     ▼
  │                                           CHECKPOINT (commit)    JAVÍTÁS ≤ 3 kör (04)
  │                                                  │                     │ továbbra is hiba
  │                                                  ▼                     ▼
  │                                           mérföldkő-kapu         ROLLBACK a legutóbbi checkpointra
  │                                                                        │
  └──────── ÚJRATERVEZÉS (csak az érintett részgráf, max 2×) ◀─────────────┘
                     │ továbbra is hiba
                     ▼
            ESZKALÁCIÓ: erősebb modell → felhasználó → őszinte feladás
```

## 2. Állapotgép

**Futás szintje:** `created → understanding → planning → executing ⇄ paused → integrating →
reporting → done`; mellékágak: `waiting_user`, `failed`, `cancelled`. A `paused` állapotba a futás
**csak feladathatáron** lép (vagy megszakított generálással, ld. 6. pont).

**Feladat szintje:**

| Állapot | Esemény | Új állapot | Mellékhatás |
|---|---|---|---|
| pending | minden `dependsOn` kész | ready | — |
| ready | az ütemező választja + szabad a sáv + (háttérfutásnál) a felhasználó tétlen | running | napló: `task.start` |
| running | kimenet megjött, formailag rendben | verifying | fájl a munkaterületre |
| running | `VOICE` kéri a sávot / a felhasználó szünetet kér | ready | generálás megszakítva, részeredmény eldobva |
| verifying | minden check zöld | done | checkpoint |
| verifying | hiba, `attempts < maxAttempts` | running (javító mód) | hibakivonat a promptba ([04](04-onellenorzes-es-javitas.md)) |
| verifying | hiba, nincs több próba | failed | eszkaláció vagy újratervezés |
| bármely | szerződést kellene módosítani | blocked | `contract.change_request` |

```ts
type JournalEvent =
  | { t: string; type: 'plan.created' | 'plan.replanned'; version: number; reason?: string }
  | { t: string; type: 'task.start' | 'task.done' | 'task.failed'; task: string; attempt: number }
  | { t: string; type: 'check'; task: string; check: string; ok: boolean; ms: number; digest?: string }
  | { t: string; type: 'llm'; task: string; model: string; tokensIn: number; tokensOut: number; ms: number }
  | { t: string; type: 'checkpoint'; task: string; commit: string }
  | { t: string; type: 'rollback'; to: string; reason: string }
  | { t: string; type: 'ask_user' | 'user_answer' | 'run.paused' | 'run.resumed' | 'run.end'; data?: unknown };
```

## 3. Ellenőrzés: olcsótól a drágáig (fail-fast)

| # | Check | Ár (becslés) | Mit fog meg |
|---|---|---|---|
| 1 | formai: egy kódblokk, a várt útvonal, nincs „…a többi változatlan” | ~0 | fecsegés, csonka kimenet |
| 2 | `parse` (`node --check`, `python -m py_compile`) | < 1 s | szintaxishiba |
| 3 | őr (`guard`): befagyasztott fájlok hash-e változatlan; tiltott importok (`child_process`, `net`, `subprocess`…, ha a feladat nem kéri); teszt nincs kikapcsolva | ~0 | szerződéssértés, veszélyes kód, teszt-csalás |
| 4 | `typecheck` / `lint` (ha a sablon tartalmazza) | 1–10 s | rossz nevek, típusok |
| 5 | a feladat saját tesztjei a sandboxban | 1–10 s | logikai hiba |
| 6 | az eddigi összes teszt (regresszió) | 1–20 s | elrontott korábbi rész |
| 7 | Kritikus (LLM) | 30–120 s | olvashatóság, hiányzó eset — **csak javaslat, nem kapu** |

Az első bukó check megállítja a sort, csak az ő kivonata megy a javításba. A 7. nem kapu: egy kis modell véleménye nem bizonyíték ([04](04-onellenorzes-es-javitas.md)).

## 4. Ellenőrzőpontok és visszagörgetés

**Javaslat:** a feladat munkaterülete egy **saját, helyi git-repó** a futási mappában (a repón kívül,
`%LOCALAPPDATA%\Auri\sandbox\runs\<runId>\`; a gépen git 2.54 van). Minden `done` feladat = egy commit (üzenet:
a feladat azonosítója + a zöld checkek); a mérföldkő-kapu után címke (`M2-ok`).

```ts
interface Checkpoint {
  runId: string; planVersion: number; taskId: string;
  commit: string;                                   // SHA a munkaterület-repóban
  checksPassed: string[];                           // pl. ["parse", "test:test/repo.test.js 6/6"]
  budgetUsed: { tokensOut: number; llmS: number; sandboxS: number }; at: string;
}
```

**Visszagörgetés** = `git reset --hard <commit>` a munkaterületen (biztonságos, mert az Auri sajátja): feladat
bukásakor a feladat **előtti** commitra, részgráf újratervezésekor a részgráf legkorábbi feladata előttire.
**Ami megmarad:** a napló (sikertelen próbák, hibaaláírások) — a bukás adat a tanuláshoz, nem ellenőrzött tudás.

## 5. Újratervezés

| Kiváltó ok | Példa |
|---|---|
| egy feladat a javítások és az eszkaláció után is bukik | a teszt 3 kör után is ugyanott hasal el |
| szerződésmódosítás kell | kiderül, hogy a `Todo`-nak kell `updatedAt` |
| a kutatás cáfolja a terv feltevését | az API nem létezik a telepített verzióban |
| a költség várhatóan > 150%-a a becslésnek | a mérföldkő a keret felénél még 1/4-nél tart |
| a felhasználó módosítja a célt | „mégis kell bejelentkezés” |

Szabályok: csak az **érintett részgráf** (a hibás feladat + leszármazottai) tervezhető újra, a kész ősök
maradnak; a tervező csak a célt, a szerződést, a hibás feladatot, az utolsó hibakivonatot és a próbák
egysoros összefoglalóit kapja; futásonként **max 2** újratervezés. Szerződésmódosításnál minden feladat,
ami a szerződést olvassa, `pending`-be kerül, de **először csak a checkje fut újra** — ha zöld,
nem kell újragenerálni. Minden tervverzió a naplóba kerül (`plan.version`).

## 6. Költségvetések és a sáv

| Szint | Keret (kiinduló, **becslés**) | Túllépéskor |
|---|---|---|
| LLM-hívás | `num_predict` ≤ 1000 token; falióra ≤ 6 perc | megszakítás → „túl nagy” → bontás |
| Feladat | 1 + 3 javító kör; ≤ 20 perc | failed → eszkaláció / újratervezés |
| Mérföldkő | ≤ 2× a terv becslése | újratervezés vagy kérdés |
| Futás | a kéréskor megadott; alap: 60 perc LLM-idő | szünet + összefoglaló + „Folytassam?” |
| Sandbox-futtatás | 30 s / tesztfuttatás, 512 MB | bukás `timeout` / `oom` kivonattal |

- **Elsőbbség:** `VOICE` (Jarvis hangkör) > `CHAT` > `TASK` (kért feladat) > `BACKGROUND` (éjszakai
  tanulás, hosszú futás folytatása). A futó generálás a stream lezárásával megszakítható (a Jarvis `agent.py`
  `aclosing` mintája). Mért ok: közös sávon az 1. token medián 3,9 s, p90 14,0 s lett (terheletlenül 0,45–0,56 s).
- **Két modell, egy CPU:** az `OLLAMA_NUM_PARALLEL=1` modellenként érvényes — amíg nincs mérve, hogy két
  betöltött modell sorban fut-e, `VOICE` alatt a futás nem indít hívást ([../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md) NK14).
- **Prefixváltás ára** (mért: e2b ~6 s, e4b ~17 s): az azonos szerepű hívások csoportosítva, a Kritikus a végén egyben.

## 7. Napló és folytathatóság

Futásonként egy append-only JSONL: `data/runs/<runId>/journal.jsonl` (a 2. pont eseményei) + a
munkaterület-repó. **Újraindítás után** a napló visszajátszása adja az állapotot: a `running` feladat
`ready`-be kerül, a munkaterület a legutóbbi checkpointra áll. Ezért minden lépés **idempotens**: a fájl
írása mindig teljes csere egy ismert alap-commitra, nem foltozás a foltozáson.

**A záró jelentés a naplóból készül, nem a modell emlékezetéből.** Ez a Jarvis hallucináció-őrének
általánosítása: ott nincs „megnyitottam” sikeres eszköz nélkül, itt nincs „kész, a tesztek zöldek” zöld
`check` esemény nélkül.

## 8. A fő ciklus (pszeudokód)

```python
async def execute(plan, ws, journal, budget):
    while (task := scheduler.next_ready(plan)) is not None:
        await lane.acquire(priority="task")            # egy Ollama-sáv; a Jarvis megelőzheti
        try:
            out = await produce(task, ws)              # LLM vagy determinisztikus (sablon, futtatás)
            digest = verify(task, ws, out)             # 3. pont; None = minden zöld
            while digest and task.attempts < task.budget.maxAttempts:
                out = await repair(task, ws, digest)   # 04: hibakivonat + jelenlegi fájl
                digest = verify(task, ws, out)
            if digest is None:
                journal.checkpoint(task, ws.commit(task)); mark_done(task)
                if milestone_complete(task): run_gate(task.milestone)
            else:
                ws.reset(last_checkpoint_before(task))
                if not await escalate(task, digest):   # erősebb modell / kérdés
                    plan = replan_subtree(plan, task, digest) if plan.replans < 2 else fail_run(task, digest)
        except Preempted:
            journal.log("run.paused"); await lane.wait_free(); journal.log("run.resumed")
        finally:
            lane.release()
        if budget.exceeded(): return pause_with_summary(plan)
    return report_from_journal(journal)                # nem a modell fogalmazza a tényeket
```

## 9. Kész, ha

- Hibabeinjektálással (szándékosan rossz kimenet) a rollback a helyes commitra áll, és a napló mutatja.
- A folyamat megölése és újraindítása után a futás a megszakított feladattól folytatódik, adatvesztés nélkül.
- Szerződésmódosításnál csak az érintett feladatok checkjei futnak újra; a zöldek nem generálódnak újra.
- `VOICE` kérésre a futás megszakított generálással vagy a következő feladathatáron átadja a sávot (a késés mérve).
- A záró jelentés minden „kész” állítása egy zöld `check` eseményre mutat a naplóban.

## Kapcsolódó

- [01-feladatbontas.md](01-feladatbontas.md) · [04-onellenorzes-es-javitas.md](04-onellenorzes-es-javitas.md) · [05-teljes-pelda.md](05-teljes-pelda.md) · [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md)
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) · [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) (ahol a checkek futnak)
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) (modell, eszkaláció, elsőbbség) · [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) · [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)
