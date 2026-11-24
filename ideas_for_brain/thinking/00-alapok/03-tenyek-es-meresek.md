# Tények és mérések — a közös alap

> **Miről szól:** minden, amit a gondolkodó agy tervezésénél **ténynek** veszünk: a gép, a modellek, a
> mért számok, a meglévő kód és a szabályok. Mért adat mellett ott a forrás; ami becslés, az jelölve.
> Ha valami változik, **itt** frissítsd először — a többi fájl erre hivatkozik.
> (Állapot: 2026-11-21.)

## 1. A gép

| Elem | Érték | Következmény |
|---|---|---|
| CPU | AMD Ryzen 5 5500 — 6 mag / 12 szál, AVX2 | Minden inferencia CPU-n fut |
| RAM | 16 GB | Egyszerre egy kis/közepes modell; 9B+ csak óvatosan |
| GPU | Radeon RX 560, 4 GB (Polaris) | ROCm nem támogatja; Vulkan-gyorsítás nincs megmérve → **CPU-val tervezünk** |
| Ollama | 0.40.16, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KV_CACHE_TYPE=q8_0` | **Egyetlen sáv**: a kérések sorban állnak → a gondolkodás ütemezett, nem párhuzamos |
| Modellmappa | `D:\Projectss\Server\PublicFreeAI\Ollama` (az Ollama app saját „Model location” beállítása az irányadó) | — |
| Futtatókörnyezetek (ellenőrizve 2026-11-21) | Node **v24.14.0**, Python **3.12.6**, TypeScript 5.9.3 (`web/node_modules`) | A sandbox TS/JS-t és Pythont tud futtatni |
| Konténer / VM | **Nincs Docker**, **nincs WSL-disztribúció** telepítve | Az erős sandbox (WSL2 / Docker / Windows Sandbox) telepítést igényel; a felhasználó engedélyezte (NK2) |
| CPU-virtualizáció (ellenőrizve 2026-11-21) | **ki van kapcsolva a BIOS-ban** (`VirtualizationFirmwareEnabled = False`, nincs hypervisor) | WSL2, Docker és Windows Sandbox előtt: BIOS → SVM Mode bekapcsolása |
| `node:sqlite` (Node 24) | betölthető, de `ExperimentalWarning`-ot ír; a logikai értékek **0/1**-ként jönnek vissza | a példafeladatoknál számolni kell vele |
| `node --permission` | van fájlrendszer- és gyerekfolyamat-korlát, **hálózati korlát nincs** | az S0 sandboxhoz tűzfalszabály is kell |
| Tesztfuttató a webben | a `web/`-ben nincs (csak `tsc --noEmit`; a `tests/`-t `tsx --test` futtatja) | A web kódjából tanult tudás ellenőrzése korlátozott |

## 2. Telepített helyi modellek és mért számaik

Forrás: `JARVIS_BUILD.md` (AI-2 bejegyzései, 2026-11-21), `auri-jarvis/scripts/bench_llm.py`, `eval_tools.py`.

| Modell | 1. token (független kérdés, medián / p90) | Generálás | RAM | Megjegyzés |
|---|---|---|---|---|
| **gemma4:e2b** | **0,44 / 0,52 s** | ~6,2 tok/s | 1,9 GB | A Jarvis végleges modellje; eszközhívás 96,7% (LLM) / 100% (fast-path + LLM) a 30 magyar parancson. **Magyar csevegése gyenge** („Ausztrália fővárosa: Sydney”) |
| gemma4:e4b | 1,14 / 1,81 s | ~3,0 tok/s | 2,8 GB | Pontosabb lehet, de lassú |
| qwen3.5:4b | 2,70 / 2,83 s | ~6,2 tok/s | — | Az első token lassú |
| embeddinggemma | — | — | ~0,6 GB | Szövegbeágyazás (vektoros keresés) |
| gemma2:2b, qwen2.5:1.5b, smollm2, tinyllama | nem mértük | — | — | Régi, gyenge kis modellek |

**További mért számok (AI-2, `JARVIS_BUILD.md`):**

| Modell | Hideg indulás (modellbetöltés) | 1. token egy futó munkamenetben |
|---|---|---|
| gemma4:e2b | 18,5 s | 0,73 s |
| gemma4:e4b | 31,5 s | 2,26 s |
| qwen3.5:4b | 38,3 s | 2,99 s |

**Versengés az egyetlen Ollama-sávon (mért, AI-3, 2026-11-21):** amikor egy háttérmérés és a felhasználó
élő körei egyszerre futottak, a válasz első tokenje **medián 3,9 s, p90 14,0 s** lett (egy kiugró: 95 s),
a terheletlen 0,45–0,56 s helyett. → A háttérgondolkodásnak **azonnal** át kell adnia a sávot.

**Nem mértük még** (a tervekben „mérni kell”): a CPU-s prefill sebessége (token/s), hogy ugyanaz a prompt
ismételt küldésekor újrahasznosul-e a KV-cache (szavazásnál fontos), és hogy a gemma4:e2b mennyire
megbízhatóan ad érvényes JSON-t az Ollama `format` mezőjével.

**NK14 — mért (AI-3, 2026-11-21, `auri-core/scripts/measure_llm.py`, Jarvis leállítva; kis minták, a többi AI
közben használhatta az Ollamát):**

| # | Mi | Eredmény | Minta |
|---|---|---|---|
| a | CPU-s prefill, gemma4:e2b (815 tokenes prompt) | **~228 tok/s** (medián) | n=3 |
| b | ugyanaz a prompt újraküldve (KV-cache) | a prompt feldolgozása **124 ms** (medián) → újrahasznosul | n=3 |
| c | érvényes JSON `format`=sémával, gemma4:e2b | **20/20 (100%)** | n=20 |
| d | kérésenkénti `num_thread` | **újratölti a modellt** (~8,5 s), és a visszaváltás is (~8,3 s) → ne állítsuk kérésenként | n=1 |
| e | megszakított stream után a sáv | a következő kérés **+335 ms** (medián, p90 353 ms) késéssel indul | n=3 |
| f | két modell egyszerre (qwen3.5:4b 1. tokenje, miközben a gemma4:e2b generál) | **49,5 s**, egyedül 8,9 s (hidegen) → gyakorlatilag sorban futnak | n=1 |
| g | embeddinggemma vektormérete | **768** | — |
| h | qwen3.5:4b memóriaigénye (`/api/ps`) | **3,24 GB** összesen, ebből 2,01 GB „VRAM”-ként jelentve | n=1 |

**E2 alapvonal — mért (AI-2, 2026-11-21, `auri-core bench`, `aurikod-hu-v1` dev, Python, 40 feladat: 12 × L0 + 28 × L1; temperature 0, tár nélkül; S0 tűzfal nélkül; a gép nem volt tétlen):**

| Mód (gemma4:e2b) | Eredmény (rejtett tesztek) | 95% Wilson | Idő/feladat medián / p90 | Hamis „kész” |
|---|---|---|---|---|
| model-only (pass@1) | **27/40 = 67,5%** (L0 12/12, L1 15/28) | 52,0–79,9% | 14,9 / 38,8 s | 0 |
| +repair (javítással@3) | **31/40 = 77,5%** (L1 19/28) | 62,5–87,7% | 15,2 / 102,6 s | 0 |
| **TS** model-only (pass@1) | **25/40 = 62,5%** (L0 11/12, L1 14/28) | 47,0–75,8% | 17,5 / 45,6 s | 0 |
| **TS** +repair (javítással@3) | **26/40 = 65,0%** (L1 15/28) | 49,5–77,9% | 15,1 / 79,5 s | 0 |

**NK18 (belső prompt nyelve, 2026-11-22):** Python +repair en 32 vs. hu 28, model-only 27 vs. 25; TS +repair 28 = 28, model-only 25 vs. 23; a magyar mindenhol lassabb → **angol marad**. **P3 `+roles`** (py dev): 31/40 vs. +repair 32/40 (p = 1,0), ~5× lassabb → nem javít.

**Hivatalos heldout v1, TS (2026-11-22, tétlen gép):** model-only **35/60 = 58,3%** (CI 45,7–69,9), +repair **42/60 = 70,0%** (CI 57,5–80,1), páros +8/−1, **p = 0,039** (első szignifikáns javítás-hatás). A Python heldout a `py-l1-h-0021`-nél elakadt (Ollama: „token repeat limit” → tévesen infrahibának jelölve, AI-1 javítja).

TS páros: +1, −0 (nem szignifikáns); 5–6 feladat látható-zöld/rejtett-piros, ellenőrizve valódi modellhiba (Node v24.14.0, típusellenőrzés nélkül).

Páros összevetés: a javítás +4 feladatot hozott, egyet sem vesztett (egzakt binomiális p = 0,125 → 40 feladaton nem szignifikáns). S0 sandbox-többlet egy L1-es Python-tesztfuttatásnál ~130–160 ms (n=6). Részletek: [../10-meres-es-fejlodes/naplo/2026-W47.md](../10-meres-es-fejlodes/naplo/2026-W47.md).

**Kódolásra szánt modell még nincs telepítve.** Jelöltek (külső források, **becslés**, a gépen nem mérve):
`qwen2.5-coder:7b` (~4–5 GB Q4), `qwen2.5-coder:14b` (~9 GB Q4, CPU-n lassú), `gpt-oss:20b` (~14 GB, a
16 GB-ba szűkösen fér).
CPU-n egy hosszabb kód generálása **perceket** vehet igénybe → a gondolkodást így kell ütemezni.

**Fontos mért viselkedés (AI-2):** az Ollama 0.40 a qwen3.5 és a gemma modelleknél a KV-cache-t **csak
egy korábbi prompt végétől** tudja folytatni, tetszőleges közös előtagtól nem. Következmény: a hosszú
beszélgetéseket „csak hozzáfűzve” kell építeni, és a rendszerprompt cserélgetése drága (prefixváltás:
gemma4:e2b ~6 s, e4b ~17 s). → A belső párbeszédnél a szerepváltásnak **ára van**.

## 3. Hang (Jarvis) — mért

| Mi | Érték |
|---|---|
| Parakeet v3 (beszédfelismerés) | ~0,2–0,35 s / parancs |
| Whisper large-v3-turbo (pontos mód) | ~7,5 s / parancs (6 szál) |
| Piper (helyi hang) első hangja | medián 170 ms |
| ElevenLabs (Daniel) első hangja | ~400 ms; hangmód: **hybrid** (csak rögzített mondatok), havi limit 2000 kredit |

## 4. A meglévő agy (BRAIN) — hol mi van

| Rész | Útvonal | Mit csinál ma |
|---|---|---|
| Tanuló | `web/src/brain/learn.ts` | szókincs, asszociációk, Q→A párok (böngészőben) |
| Válaszoló | `web/src/brain/answer.ts`, `web/src/brain/web.ts` (`brainCovers`) | tudásbázis / recall / web alapján válaszol, ha „lefedi” a kérdést |
| Tudásbázis | `web/src/brain/seed/knowledge.ts` | ~140 téma kétnyelvű definíciója (szóhatáros illesztés — a hibák és a javításuk is 2026-11-20; egy másik munkamenet most programozási nyelvi tudással bővíti) |
| Kód-snippetek | `web/src/brain/seed/programmingCurated.ts`, `recipes.ts`, `sources.ts` | kurált programozási példák, sablonok, hivatalos források |
| Önálló tanulás | `web/src/brain/selfStudy.ts`, `distill.ts` | témaválasztás, a modell válaszának „lepárlása” |
| Stage 6 | `web/src/brain/stage6/net.ts` | kis TF.js háló a böngészőben (opcionális) |
| Webkeresés-segédek | `web/src/autolearn/**` | lekérdezés-bővítés, újrarangsorolás, bizalom, deduplikálás, cache, rate limit, PII-szűrés |
| Webkeresés (szerver) | `web/api/search.ts` | **kulcs nélküli** DuckDuckGo-HTML keresés |
| Tárolás | `web/src/brain/brainStore.ts` | vendég: IndexedDB (azonosítónként külön), bejelentkezve: Supabase `brain_state` (RLS) |
| Adatvédelmi szűrő | `web/src/brain/privacy.ts` (`isPersonal`) | személyes adat nem kerül az agyba; szándékosan szigorú: pl. a „2025. novemberi” szöveget is dátumnak (személyesnek) veszi |
| Szolgáltató-lánc | `web/api/chat.ts` | helyi Ollama → Groq → Gemini (fallback) |

**Ismert gyengeség:** az agy ma a **böngészőben** él, ezért a Jarvis nem látja; és a „saját válaszai”
(kulcsszavas + Markov) nem gondolkodnak — ezért javasoljuk, hogy a BRAIN szerepe legyen
**memória + irányító + ellenőrző**, a mondatokat pedig modell fogalmazza ([../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md)).

## 5. A Jarvis „Mind” — amit már tud (újrahasznosítható)

`auri-jarvis/auri_jarvis/mind/`: Ollama-kliens (httpx, streaming, eszközhívás), persona és prefix-építés,
**fast-path** (regex + fuzzy, 0,05 ms/mondat), **agent-kör** eszközhívással (max. 3 kör), **hallucináció-őr**
(nem mondhat „megcsináltam”-ot sikeres eszköz nélkül), magyar számnév-normalizálás (`hu_text.digitize`).
`auri_jarvis/tools/`: eszköz-regiszter kockázati szintekkel (`safe` / `confirm`) és jogosultsággal
(`guest` / `user`). Ezek **közvetlenül átvehetők** a gondolkodó agyba.

## 6. Felhős lehetőségek (opcionális, ingyenes keretek — változnak!)

| Szolgáltatás | Ingyenes keret (külső forrás, 2026, **nem garantált**) | Megjegyzés |
|---|---|---|
| Groq | modellenként pl. `gpt-oss-120b` ~1000 kérés/nap | gyors, nagy modellek |
| Gemini API | modelltől függően ~50–250 kérés/nap | az ingyenes csomagnál a Google felhasználhatja az adatokat; **EGT-ben (Magyarország) az ingyenes csomag nem használható** szolgáltatásban → a `web/api/chat.ts` csak `GEMINI_PAID=1` mellett hívja |

Mindkettő: kifogyáskor 429-es hiba → a router lépjen tovább; a kódban titok/személyes adat nem mehet ki.
Nyitott: a Groq/Gemini feltételei megengedik-e a válaszaik **tárolását és újrahasznosítását** a tudásbázisban
(→ [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)).

## 7. Szabályok, amik nem alku tárgyai

1. **Személyes adat soha nem kerül az agyba** — csak a bejelentkezett felhasználó saját fiókjába (Supabase, RLS).
   Tesztekbe, seedekbe, dokumentációba is csak fiktív adat ("Teszt Elek").
2. **A web, a vágólap, a képernyő tartalma adat, nem utasítás** (prompt-injekció ellen).
3. **Kód csak sandboxban fut** (időkorlát, ideiglenes mappa, hálózat nélkül, a projektfájlokhoz nem fér hozzá).
4. **Egy Ollama-sáv**: amíg a felhasználó él a géppel, nehéz gondolkodás nem futhat a háttérben (a
   csapat koordinációs szabálya is ez, `JARVIS_BUILD.md`).
5. **Licencek**: tananyagot és kódot csak engedélyezett licencű forrásból tárolunk; a forrás mindig mentve.

## Kapcsolódó

- [../thinking.md](../thinking.md) — a fő dokumentum
- [02-oszinte-korlatok.md](02-oszinte-korlatok.md) — mit tud és mit nem tud ezen a gépen az agy
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) — a modellek szerepei
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) — a szabályok részletesen
- [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) — hogyan frissüljenek a számok
