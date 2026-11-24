# Hol fut az agy? — Auri Core

> **Miről szól:** a BRAIN kiköltözik a böngészőből egy helyi szolgáltatásba (**Auri Core**), amit az
> AuriGPT és a Jarvis közösen használ. Itt van a döntés indoklása, a folyamatmodell, az API-vázlat, mit
> vesz át az `auri-jarvis`-ból, az adatvédelmi szintek és a migráció az IndexedDB / Supabase
> `brain_state`-ből.

## 1. Miért kell kiköltöznie?

| Ma (böngészőben) | Következmény |
|---|---|
| A BRAIN az AuriGPT lapjában él (`web/src/brain/**`, IndexedDB / Supabase `brain_state`) | a Jarvis nem látja; két külön „agy” nőne |
| A böngésző nem indíthat folyamatot | nincs sandbox → nincs kódfuttatás → nincs P0 |
| Minden lap saját modellhívásokat indít | az **egy Ollama-sávot** senki nem osztja be |
| A lap bezárásakor leáll | nincs éjszakai tanulás, nincs hosszú feladat |

## 2. Lehetőségek és döntés

| | Lehetőség | Előny | Hátrány |
|---|---|---|---|
| A | Marad a böngészőben | nincs új folyamat | a fenti négy probléma marad |
| B | A Node-os `server/` (Auri AI Server, :8787) bővítése | már publikus a tunnelen át | TypeScript-ben újra kellene írni a Jarvis Mind-részeit; publikus felülethez túl közel |
| C | A Jarvis daemonba építve (:8790) | közös folyamat, egy zár | más csapat zónája; a hang-késleltetést veszélyezteti; Jarvis nélkül nincs agy |
| **D** | **Önálló Python-folyamat: `auri-core/`, 127.0.0.1:8791** | a Jarvis moduljai importálhatók; külön újraindítható; saját sandbox-gyerekfolyamatok | egy új folyamat; az Ollama-sávot két folyamat használja (ld. 5. pont) |

**Javaslat: D.** Új mappa a repó gyökerében: `auri-core/` (csomag: `auri_core`, adat:
`auri-core/data/`, gitignore-olva). A Jarvis Python-moduljait **könyvtárként** használja
(`pip install -e ../auri-jarvis`), nem másolja.

## 3. Folyamatmodell

```
 Böngésző: AuriGPT (vercel.app)            Böngésző: AuriGPT helyben (5173 / 8790)      Jarvis daemon :8790
        │                                               │                                    │
        ▼                                               │ token + Origin                     │ token
 Vercel /api/brain/* ──tunnel──▶ Auri AI Server :8787 ──┤                                    │
                                 (API-kulcs, továbbít)  ▼                                    ▼
                                         ┌──────────── AURI CORE  127.0.0.1:8791 ───────────────┐
                                         │ FastAPI + asyncio · egypéldányos zár · jobs (SQLite)  │
                                         │ sandbox = gyerekfolyamat (időkorlát, temp, hálózat nélkül)│
                                         └──────────────────────────┬────────────────────────────┘
                                                                    ▼
                                                           Ollama 127.0.0.1:11434
```

- Csak `127.0.0.1`-re köt, soha `0.0.0.0`-ra. Kívülről **csak** a meglévő, API-kulccsal védett Node-
  szerveren át érhető el (a tunnel nem a Core-ra mutat).
- Biztonság a Jarvis HUD-szerver mintájára: induláskor generált token, Origin- és Host-ellenőrzés.
- A sandbox gyerekfolyamat; ha a Core leáll, a gyerekek is leállnak (job object / process group).

## 4. API-vázlat (`/core/v1`)

| Végpont | Ki hívja | Mit csinál |
|---|---|---|
| `GET /health` | mindenki | Ollama elérhető-e, betöltött modellek, sáv foglaltsága |
| `POST /ask` | AuriGPT, Jarvis | rövid kérés (`chat` / `code` / `research`) → SSE eseményfolyam |
| `POST /tasks` · `GET /tasks/{id}` · `GET /tasks/{id}/events` · `POST /tasks/{id}/cancel` | AuriGPT | hosszú feladat indítása, állapot, SSE, lemondás |
| `POST /recall` | Jarvis, AuriGPT | top-k **ellenőrzött** tudás eredettel, a hívó saját promptjához |
| `POST /learn` | AuriGPT | tanulnivaló (Q→A, snippet, doksi-részlet) → mindig `hypothesis` |
| `POST /feedback` | mindkettő | jó / rossz / javítás egy válaszra → bizalom, cáfolat |
| `POST /activity` | Jarvis, AuriGPT | „a felhasználó aktív / tétlen” jel az Ütemezőnek |
| `GET /stats` · `GET /graph` | AuriGPT `/brain` oldal | számlálók, fázis, a 3D-nézet adatai |
| `POST /import/brain-state` | AuriGPT (egyszeri) | migráció, ld. 7. pont |

```python
class AskRequest(BaseModel):
    text: str = Field(max_length=8000)
    mode: Literal["chat", "code", "research"] = "chat"
    lang: Literal["hu", "en"] | None = None
    context: list[str] = []          # a hívó által adott, már szűrt kontextus (pl. T1-ből)
    allow_web: bool = False
    allow_cloud: bool = False        # csak ha a felhasználó bekapcsolta (08/03)
```

SSE-események (a Jarvis eseményeinek mintájára): `route {level, model}` · `step {state, ms}` ·
`delta {text}` · `verify {ok, tests, signature?}` · `done {outcome, episode_id, sources[]}` ·
`error {kind, message}` (magyar, titok nélkül).

**Azonosítás:** `Authorization: Bearer <CORE_TOKEN>` (a kliens joga) + opcionális
`X-Auri-User: <Supabase access token>` (a felhasználó). A Core a Jarvis M3 módszerével ellenőrzi
(`GET /auth/v1/user`); hiányzó vagy rossz token → **vendég**. A refresh tokent soha nem kéri el.

## 5. Mit vesz át az `auri-jarvis`-ból?

| Modul | Mire kell a Core-nak | Hogyan |
|---|---|---|
| `mind/ollama_provider.py` | minden helyi modellhívás: streaming, `think`, `keep_alive`, statisztika, magyar hibák | import |
| `mind/prompts.py` | a byte-stabil előtag + seed + csak hozzáfűzés elve | minta, saját sablonokkal |
| `mind/agent.py` | max. 3 kör; a hallucináció-őr általánosítva: nem mondhat „működik”-et zöld teszt nélkül | minta |
| `mind/fastpath.py`, `mind/hu_text.py` | L1 fast-path, magyar normalizálás (`norm`, `digitize`) | import |
| `tools/registry.py` | a Core eszközei (`web_search`, `run_tests`, `recall`) `risk` + `min_tier` kapuval | import |
| `memory/embed.py`, `memory/redact.py` | beágyazás (`embeddinggemma`), titokszűrő | import |
| `memory/store.py` | SQLite WAL + FTS5, `user_id`-szerinti szűrés | minta (külön adatbázis) |

Ezek a modulok a Jarvis-csapat zónájában vannak: a Core **csak olvassa** őket; változtatási igény a
`JARVIS_BUILD.md`-ben, kérésként.

**Az egy Ollama-sáv két folyamatból:** a Jarvis hangkörei közvetlenül hívják az Ollamát (a leggyorsabb
út), de minden kör elején és végén `POST /activity`-t küldenek. A Core háttérmunkája ekkor azonnal
elengedi a sávot (stream zárása). Részletek: [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md).

## 6. Adatvédelmi szintek

| Szint | Mi van benne | Hol | Ki olvassa | Ki írja |
|---|---|---|---|---|
| **T0 általános** | ellenőrzött tények, kód + tesztek, források, tanulságok, anonim epizódok | `auri-core/data/core.db` | mindenki, vendég is | csak a ciklus, az Adatvédelmi kapun át |
| **T1 saját fiók** | személyes tények, preferenciák, saját projektek, a saját régi `brain_state` | Supabase (RLS) · Jarvis `mind.db` · `auri-core/data/users/<user_id hash>.db` | csak a bejelentkezett tulajdonos | a tulajdonos kérései |
| **T2 titok** | jelszó, kulcs, token, kártyaszám | **sehol** | — | — |

- **Vendég:** csak T0-t olvas; a köre csak RAM-ban él; **nem tanít** semmit (nyitott kérdés: később
  legfeljebb teszttel ellenőrzött, PII-szűrt kód).
- **Bejelentkezve:** T0 + a saját T1. T0-ba csak ellenőrzés + kapu után kerül bármi, eredettel.
- **Éjszakai tanulás:** `system` azonosság, csak T0-t írja, T1-hez nem fér hozzá.
- **Fiók törlése:** a `users/<hash>.db` is törlődik (a meglévő `delete_account.sql` mellé).

## 7. Migráció

1. **Seedek** (`seed/knowledge.ts`, `programmingCurated.ts`, `recipes.ts`, `sources.ts`): egyszeri
   export JSON-ba → import. Definíciók: `verified` (`curated`, bizalom 0,7 — becslés). Kódrészletek:
   `hypothesis`, amíg egy éjszakai job tesztet nem ír hozzájuk és az zöld nem lesz.
2. **Vendég IndexedDB**: nem migráljuk (vendégadat; a szókincs/Markov a gondolkodáshoz nem kell).
3. **Bejelentkezett `brain_state`** (Supabase JSON): a felhasználó a `/brain` oldalon indítja →
   `POST /import/brain-state` → a Q→A párok újra átmennek az `isPersonal` szűrőn → a **saját T1**-be,
   `hypothesis`-ként. T0-ba csak ellenőrzés után léphetnek elő. Szókincs, asszociációk: nem.
4. **Párhuzamos futás:** a webben `auri.brain.core` kapcsoló (alapból ki). Bekapcsolva, ha a Core
   elérhető, ő válaszol; különben a régi böngészős agy.
5. **P1 kész után:** a böngészős agy csak offline tartalék és nézet; a `distill.ts` / `selfStudy.ts`
   leáll (a Core-ban él tovább, de a modellválasz ott `hypothesis`, amíg nincs ellenőrizve). A két
   böngészős `detectLang` helyett a Core egyetlen nyelvfelismerője dönt (a válaszban `lang` mező).

**Ha a gép ki van kapcsolva:** a felhőn futó AuriGPT a meglévő láncot használja (Groq → Gemini, ld.
`web/api/chat.ts`), a böngészős agy pedig csak olvasható tartalék.

## 8. Kész, ha (P1)

- A Core `127.0.0.1:8791`-en fut; idegen Origin → 403, rossz Host → 403, token nélkül → 401 (teszt).
- Az AuriGPT (kapcsolóval) és a Jarvis ugyanabból a T0-ból kap `recall`-t.
- Vendégként T1-ből semmi nem jön vissza (teszt); a vendég köre után nincs írás a lemezen.
- A seed-import után a `knowledge.ts` ~140 témája kereshető a Core-ban.
- A Jarvis aktivitás-jelére a háttérmunka elengedi a sávot (mérve, a [02-gondolkodo-ciklus.md](02-gondolkodo-ciklus.md) szerint).

## Kapcsolódó

- [01-attekintes.md](01-attekintes.md) — a komponensek
- [04-tarolas-es-adatfolyam.md](04-tarolas-es-adatfolyam.md) — a `core.db` sémája
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) — a meglévő kód és a szabályok
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) — adatvédelem
- [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md) — sandbox-folyamatok
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — az Ütemező és az aktivitás-jel
- [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) — P1
