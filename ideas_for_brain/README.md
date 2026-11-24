# ideas_for_brain — Auri agyának ötletei és tervei egy helyen

> Itt van minden, amit Auri **agyáról** (BRAIN) kitaláltunk, megterveztünk vagy promptként megírtunk.
> Az élő kód továbbra is a helyén van (`web/src/brain/**`, `web/src/autolearn/**`, `auri-jarvis/`).
> (Összegyűjtve: 2026-11-21.)

## Tartalom

| Mappa | Mi van benne |
|---|---|
| [thinking/](thinking/thinking.md) | **ÚJ — a gondolkodó agy terve:** helyi AI-okkal gondolkodik, keres és szörfözik a neten, értelmes mondatokat alkot, beszélget a helyi modellekkel, tanul — **elsősorban programozásra és komplex feladatokra**. Kezdd a [thinking.md](thinking/thinking.md)-vel. |
| [ai_prompts.md](ai_prompts.md) | **A `thinking/` terv felosztása 3 AI-ra:** AI-1 MIND (gondolkodó ciklus), AI-2 HANDS (sandbox, feladatkészlet, mérés), AI-3 BODY (váz, modellhívás, tár, szolgáltatás). Zónák, közös szabályok, 3 indító prompt és a közös tábla. |
| [brain/](brain/) | `BRAIN.md` — a BRAIN eredeti, nagy specifikációja (memória, „literal agy”, szakaszok, 3D nézet). `BRAIN_BUILD.md` — a BRAIN-építő AI-csapat koordinációs táblája (a státusz-logot **itt** kell folytatni). |
| [prompts/](prompts/) | A BRAIN-t építő AI-ok indító promptjai: `brain-ai-1-mind`, `brain-ai-2-eyes`, `brain-ai-3-body`, `brain-autolearn`, `brain-hybrid-ollama`. |
| [autolearn/](autolearn/) | A webes tanulás tervjegyzetei: `ALWAYS_LEARN`, `INGEST_WEB`, `INTEGRATION`, `PROGRAMMING_PERSONA`. (A modul README-je a kód mellett maradt: `web/src/autolearn/README.md`.) |

## Honnan jöttek (áthelyezés, 2026-11-21)

| Régi hely | Új hely |
|---|---|
| `web/BRAIN.md` | `brain/BRAIN.md` |
| `web/BRAIN_BUILD.md` | `brain/BRAIN_BUILD.md` |
| `web/prompts/brain-*.md` (5 db) | `prompts/` |
| `web/src/autolearn/{ALWAYS_LEARN,INGEST_WEB,INTEGRATION,PROGRAMMING_PERSONA}.md` | `autolearn/` |

A régi helyeken rövid „➜ Áthelyezve” mutató maradt, hogy a régi hivatkozások ne vezessenek sehova.

**Nem kerültek ide** (szándékosan): a Jarvis dokumentumai (`jarvis_reboot_to_auri.md`, `JARVIS_BUILD.md`,
`auri-jarvis/prompts/`) — azok a hangos asszisztensről szólnak, és a 3 építő AI éppen használja őket;
valamint a kód által betöltött fájlok (`auri-jarvis/config/persona.md`, `me.md`).
