# auri-core

Auri helyi gondolkodó agya (P0: programozási ciklus, P1: helyi szolgáltatás). Spec: `../ideas_for_brain/thinking/`, munkamegosztás: `../ideas_for_brain/ai_prompts.md`.

```powershell
cd auri-core
.venv\Scripts\python -m pytest                      # offline, Ollama nélkül
.venv\Scripts\python -m auri_core run tasks/py-l1-0001
.venv\Scripts\python -m auri_core serve             # P1: http://127.0.0.1:8791/core/v1 (Ctrl+C: leállítás)
.venv\Scripts\python -m auri_core migrate-seeds     # a web BRAIN seedjei → közös tudás (újrafuttatható)
.venv\Scripts\python -m auri_core bench --mode +cloud --from-bench <dev +repair bench_id>   # L4-mentés mérése, Ollama nélkül; kell: AURI_CORE_GROQ_API_KEY (.env), heldoutra nem fut
.venv\Scripts\python scripts\measure_llm.py         # NK14, valódi Ollama, csak tétlenségben
.venv\Scripts\python scripts\measure_preempt.py     # P1: /activity → sáv elengedése (Ollama, tétlenségben)
```

## Szolgáltatás (P1)

- Csak `127.0.0.1`-en indul. Rossz Host → 403, idegen Origin → 403, token nélkül → 401.
- Token: `data/core.token` (első indításkor jön létre) → `Authorization: Bearer <token>`.
- Bejelentkezés: `X-Auri-User: <Supabase access token>` (ellenőrzés: `AURI_CORE_SUPABASE_URL` + `_ANON_KEY`).
  Nélküle vendég: csak a közös tudást (T0) olvassa, semmit nem ír.
- Végpontok (`/core/v1`): `GET /health` · `GET /whoami` · `POST /ask` (SSE) · `POST /recall` · `GET /stats` ·
  `POST /learn` · `POST /feedback` · `POST /activity` · `POST /import/brain-state` · `DELETE /account`.
- Webes kliens: `web/src/core-client/` (kapcsoló: localStorage `auri.brain.core = "1"`, alapból ki).

Beállítások: `AURI_CORE_*` környezeti változók vagy `.env` (minta: `.env.example`). Adat: `data/` (nem kerül gitre).

## Mit tud ma (mérve, gemma4:e2b, helyben, 2026-11-24)

| Képesség | Állapot | Mérés |
|---|---|---|
| Kódfeladat tesztekkel (`/ask` `code`+`task`): ír → sandboxban futtat → javít (≤ 3 kör) → csak zöld tesztre „kész” | **működik** | Python dev: 27/40 → **32/40** javítással · Python heldout: 36/60 → **44/60** · TS dev: 25 → 28/40 · TS heldout: 35/60 → **42/60** (p = 0,039) · hamis „kész”: **0** minden mérésben |
| Megoldott feladat a tárból, modellhívás nélkül | működik | 0 LLM-hívás, csak a tesztek újrafuttatása |
| Csevegés (`/ask` `chat`), magyarul is | működik | ~10 s egy rövid válasz; nem ellenőrzött |
| Webes kutatás forrásokkal (`research`, `allow_web`) | működik, lassú | 7/8 helyes, medián 55 s, más nyelvű válasz: 0 (előtte 1, javítva); igazolt állítás (2 független + A/B forrás) ritka, a többi „valószínű” címkét kap |
| Többlépéses mini-projekt (`plan=True`, `/tasks`) | **gyenge** (gemma4:e2b) | **1/5** projekt (előtte 0/5), kész lépések 15/24 (előtte 3/24). 1 hamis „kész”: a modell saját tesztjei zöldek voltak, a rejtett elfogadási tesztek pirosak → a válasz most jelzi, hogy a teszteket is Auri írta (`tests_source: "own"`). A fő korlát: a kis modell rossz teszteket ír |
| Szerepek vitája (`roles`) | **alapból ki** | 31/40 vs. 32/40 javítással, ~5× lassabb → nem éri meg |
| Felhő (L4, Groq gpt-oss-120b) a helyben bukott feladatokra | alapból ki; mérve **működik** | csak bejelentkezve, kérésenkénti engedéllyel; személyes adat soha. **Dev, rejtett teszttel, a helyi sandbox dönt (2026-11-24):** Python 32 → **37/40**, TS 28 → **36/40**, hamis „kész” 0. A maradék 7 közül 6-ot a személyes-alakú adat (telefonszám, dátum) miatt a szűrő nem engedett ki, 1 túlillesztett (látható zöld, rejtett piros → bukásnak számít). Heldouton nem mértem (egyszeri mérés) |
| Tétlenkori önálló tanulás (P4) | **csak a váz** | a karbantartás fut; a gyakorló/ismétlő/webes tanulómunkák nincsenek megírva |

**Mire jó:** kis, pontosan leírt függvényekhez helyi, ingyenes, privát kódsegéd, amely nem hazudik: ami „kész”, annak a tesztjei zöldek. A nehezebbeknél, ha a helyi modell elbukik és a felhő engedélyezett, egy erősebb külső modell próbál, de ugyanazok a helyi tesztek döntenek.
**A felhő korlátai (mérve):** a Groq ingyenes kerete ~25 gyors hívás után 429-et adott, a kliens ilyenkor a napra kizárja a szolgáltatót (a mérésnél 2 feladatot újra kellett próbálni); a felhő nem tudja kikényszeríteni a válaszsémát (a gpt-oss `{"files": {"solution.py": …}}` alakot ad, ezt az `l4.canonical_files` fogadja el; a szigorú helyi `pick_solution` nem változott).
**Mire nem (még):** nagyobb, többfájlos projektek és nehéz feladatok (a 2B-s modell a korlát), és valódi önálló tanulás.
A legnagyobb javulást egy erősebb kódoló modell hozná (NK3).
