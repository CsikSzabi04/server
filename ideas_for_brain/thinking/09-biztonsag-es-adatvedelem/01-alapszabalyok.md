# Alapszabályok — a szabálykészlet és hol érvényesül

> **Miről szól:** a gondolkodó agy nem alku tárgyát képező szabályai egy helyen. Mindegyiknél: hol
> érvényesül ma a kódban, melyik teszt bizonyítja, és melyik „kapu” őrzi az Auri Core-ban. A teljes
> AuriGPT-szabályzat a `SECURITY.md`; ez a fájl annak a gondolkodó agyra szabott kivonata és bővítése.

## 1. A szabályok és a mai állapot

| # | Szabály | Ma érvényesül (kód) | Teszt | Állapot |
|---|---|---|---|---|
| SZ1 | Személyes adat soha nem kerül az agyba — csak a bejelentkezett fiók saját tárolójába | `web/src/brain/privacy.ts` `isPersonal`; `useBrainLearning` (`observe`, `distill`, `scrubPersonal`); `answer.ts` recall; `lib/memStore.ts` | `web/tests/brain-answers.test.ts`, `privacy-isolation.test.ts` | megvan (böngésző) |
| SZ2 | Titok (jelszó, kulcs, kártya, azonosító) nem lesz emlék vagy tudás | `web/src/lib/secrets.ts` `containsSecret`, `redactSecrets` | `secrets-and-providers.test.ts` | megvan |
| SZ3 | A keresőhöz csak tisztított kérdés megy | `web/src/autolearn/redact.ts` `redactForSearch` | nincs külön teszt | részben |
| SZ4 | Web, dokumentum, vágólap, képernyő és eszközkimenet **adat, nem utasítás** | `SECURITY.md` 12.1; a Jarvis `<kontextus>` csomagolása | nincs | részben |
| SZ5 | Kód csak sandboxban fut | — | — | terv (P0) |
| SZ6 | A modell kimenete nem megbízható: jóváhagyás nélkül nem lesz belőle parancs, SQL, URL-hívás | `SECURITY.md` 12.5; Jarvis hallucináció-őr | `auri-jarvis/tests/mind/test_mind_agent.py` | részben |
| SZ7 | Eszköz csak kockázati szinttel (`safe`/`confirm`) és jogosultsággal (`guest`/`user`) | `auri-jarvis/auri_jarvis/tools/registry.py` | `auri-jarvis/tests/mind/test_mind_tools.py` | megvan (Jarvis) |
| SZ8 | Felhasználók elkülönítése | Supabase RLS (`auth.uid() = user_id`), `lib/storageScope.ts`, `persist()` csak a betöltött identitásba | `privacy-isolation.test.ts` | megvan |
| SZ9 | Felhő felé nem megy titok és személyes adat; a Gemini ingyenes kerete EGT-felhasználónál tilos | `web/api/chat.ts` (`GEMINI_PAID`) | `secrets-and-providers.test.ts` | részben |
| SZ10 | Egy Ollama-sáv: a felhasználó elsőbbsége; nehéz háttérmunka csak tétlenségben | `JARVIS_BUILD.md` koordinációs kérés (emberi szabály) | — | terv (P4-ütemező) |
| SZ11 | Csak engedélyezett licencű tartalom, mindig forrással | `seed/sources.ts` (hivatalos linkek) | — | részben |
| SZ12 | A felhasználó lát, javít, töröl és exportál mindent, ami róla tárolva van | `SECURITY.md` 13.3; `components/MemoryView.tsx` | — | megvan (AuriGPT) |
| SZ13 | Tesztben, seedben, dokumentációban csak fiktív adat | konvenció („Teszt Elek”, „Minta Máté”) | kódátnézés | megvan |
| SZ14 | Az önálló folyamat korlátos: keret, kikapcsolható, csak helyi modell | `auri.brain.selfStudy` (alapból KI), max. 40 kör/munkamenet | — | részben: Ollama nélkül felhőre eshet |
| SZ15 | Kiértékelő (held-out) feladat nem tanulható | — | — | terv |

## 2. Hat kapu az Auri Core-ban

A szabályokat **kód** érvényesíti, nem a prompt. A rendszerprompt nem biztonsági határ (`SECURITY.md` 12.7).

```
 felhasználó ─▶ [K1 bemenet] ─▶ gondolkodó ciklus ─────────────────▶ [K6 kimenet] ─▶ felhasználó
                     │             │            │             │
                     │        [K3 kifelé]  [K4 futtatás]  [K5 eszköz]
                     │             │            │             │
                     │        web / felhő    sandbox     Jarvis-eszközök
                     ▼
              [K2 tanulás: canLearn()] ─▶ karantén ─▶ tudástár
```

| Kapu | Mit ellenőriz | Szabályok |
|---|---|---|
| K1 bemenet | identitás (fiók / vendég); minden szövegdarab `taint` címkét kap (`user`, `web`, `doc`, `tool`, `model`) | SZ1, SZ4, SZ8 |
| K2 tanulás | `canLearn()` — T1–T9 tiltások ([../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md)) | SZ1, SZ2, SZ11, SZ15 |
| K3 kifelé | `redactForSearch`, `containsSecret`, `isPersonal`; kvóta és engedély felhőhöz | SZ3, SZ9, SZ14 |
| K4 futtatás | csak sandbox, korlátokkal ([03-kodfuttatas-veszelyei.md](03-kodfuttatas-veszelyei.md)) | SZ5 |
| K5 eszköz | kockázat, jogosultság, megerősítés, **a hívás eredete** (adatból jött-e) | SZ4, SZ6, SZ7 |
| K6 kimenet | megjelenítés előtti tisztítás (XSS), nincs automatikus kép- vagy linkbetöltés | SZ6 |

```ts
// core/policy — tiszta függvények, egy helyen, mindegyikhez teszt
interface GateDecision { gate: 'K1' | 'K2' | 'K3' | 'K4' | 'K5' | 'K6'; allow: boolean;
                         rule?: string; at: string; subjectHash?: string }   // szöveg SOHA
```

Minden kapu-döntés naplózódik, de **tartalom nélkül**: kapu, szabálykód, időbélyeg, hash. A
tiltások száma mérőszám ([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

## 3. Elsőbbség ütközéskor

1. **Adatvédelem és biztonság** (SZ1, SZ2, SZ5, SZ8) — mindig nyer.
2. **A felhasználó munkája** (SZ10) — a tanulás vár.
3. **Tanulás és teljesítmény.**

Példák: ha egy ellenőrzéshez webkeresés kellene, de a kérdést nem lehet személyes adat nélkül
megfogalmazni → nincs keresés, az elem karanténban marad. Ha egy felhős modell gyorsabban
megoldaná a feladatot, de a kódban titok lehet → nincs felhő, helyi modell vagy feladás.

## 4. Ha egy szabály sérül

1. **Azonnal** kikapcsoljuk az érintett utat (feature flag), hogy a hiba ne terjedjen.
2. **Naplózzuk** (`ideas_for_brain/brain/BRAIN_BUILD.md` vagy a Core naplója): mi történt —
   valós személyes adat nélkül, fiktivizálva.
3. **Regressziós teszt** fiktív adattal, ami a régi kódon elbukik.
4. **Javítás**, majd **visszamenőleges takarítás** (a tudástár újraszűrése a kapun).
5. Ha személyes adat érintett: adatvédelmi incidens-vizsgálat a `SECURITY.md` és a
   `docs/adatvedelem/` szerint.

A minta a 2026-11-20-i eset (kijelentkezve felmondott profil):
[../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md).

## 5. Ellenőrzőlista új funkcióhoz

- [ ] Ír a tudástárba? → csak `canLearn()`-en át, a karanténba.
- [ ] Küld adatot ki (web, felhő)? → K3, és a felhasználó tudja, hogy külső szolgáltatót hív.
- [ ] Futtat kódot vagy parancsot? → K4 sandbox; a valódi gépen csak megerősítéssel (K5).
- [ ] Olvas külső szöveget? → `taint` címke, adatként csomagolva a promptban.
- [ ] Fut a háttérben? → tétlenség-kapu, keret, kikapcsoló.
- [ ] Van teszt fiktív adattal, és a kapu-döntés naplózva van tartalom nélkül?

## Kész, ha

- minden S-szabályhoz van legalább egy automatikus teszt (P1 végére), és a táblázat „Állapot”
  oszlopa naprakész;
- a hat kapu egyetlen `policy` modulban él, és nincs útvonal, ami megkerüli (kódátnézési szabály +
  egy teszt, ami minden tárolóírást a kapun keresztül vár);
- a kapu-napló tartalmat nem tárol.

## Kapcsolódó

- [02-prompt-injekcio.md](02-prompt-injekcio.md) · [03-kodfuttatas-veszelyei.md](03-kodfuttatas-veszelyei.md)
- [../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
- [../01-architektura/01-attekintes.md](../01-architektura/01-attekintes.md) · [../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md)
