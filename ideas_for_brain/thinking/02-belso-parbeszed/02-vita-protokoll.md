# Vita-protokoll — javaslat, kritika, javítás, döntés

> **Miről szól:** a belső vita pontos menete (javaslat → ellenőrzés → kritika → javítás → döntés), a
> megállási feltételek, a szavazás (self-consistency), a CPU-s költségkeretek, az átirat formátuma és
> hogy mi marad meg belőle. A szereplők: [01-szerepek.md](01-szerepek.md).

## 1. A protokoll egy képen

```
 FELADAT ─▶ (Kérdező, ha kell) ─▶ [Tesztelő: tesztek] ─▶ GONDOLKODÓ: javaslat
                                                          │
                     ┌────────────────────────────────────┘
                     ▼
            DETERMINISZTIKUS ELLENŐRZÉS (fordítás · teszt · lint · forrás-egyezés)   ← mindig ez az első
                     │
           zöld ─────┼──────────── piros / nincs mit futtatni
             │                      ▼
             │            KRITIKUS (csak ha a hiba oka nem egyértelmű, vagy nincs teszt)
             │                      ▼
             │            GONDOLKODÓ: javítás (a hibalista pontjaira hivatkozva)
             │                      └──▶ vissza az ellenőrzésre (kör++)
             ▼
          DÖNTÉS (szabály, nem modell) ─▶ elfogad / feladja / segítséget kér ─▶ TANÁR (később, tétlenségben)
```

Két elv: **(1) az ellenőrzés előzi meg a kritikát** — a modell-kritika csak ott dolgozik, ahol a
gép nem tud dönteni; **(2) a Tanár lépése halasztható** — az átirat elmentődik, a tanulság-kártyát
a Tanár akkor írja meg, amikor a felhasználó nem használja a gépet (egy Ollama-sáv).

## 2. A lépések

| # | Lépés | Ki | Kihagyható? | Kimenet |
|---|---|---|---|---|
| 1 | Megértés | Kérdező | igen, ha a feladat egyértelmű (rövid, ismert minta, tudástár-találat) | részkérdések, `ask_user` |
| 2 | Tesztek | Tesztelő / kész tesztek | nem kódnál nem értelmezhető | tesztfájl(ok) |
| 3 | Javaslat | Gondolkodó | nem | terv + teljes fájlok |
| 4 | Ellenőrzés | sandbox / forrás-összevetés | **nem** | `CheckResult` (exit code, összefoglaló) |
| 5 | Kritika | Kritikus | igen, ha a 4. egyértelmű hibát adott (pl. `AssertionError` egy sorral) | `issues[]`, `verdict` |
| 6 | Javítás | Gondolkodó | — | új teljes fájlok + `addresses: [issue-id]` |
| 7 | Döntés | kód | nem | `accept` / `give_up` / `ask_help` |
| 8 | Tanulság | Tanár | halasztható | tanulság-kártya |

## 3. A döntés szabályai (kód, nem modell)

```ts
function decide(s: DebateState): 'continue' | 'accept' | 'give_up' | 'ask_help' {
  if (s.check?.passed && !s.blockingIssues.length) return 'accept';          // a valóság szerint jó
  if (s.kind === 'text' && s.critique?.verdict === 'accept') return 'accept'; // nincs mit futtatni
  if (s.round >= s.maxRounds) return s.mode === 'interaktiv' ? 'ask_help' : 'give_up';
  if (s.budget.msLeft <= 0 || s.budget.outTokensLeft <= 0) return 'ask_help';
  if (isOscillating(s)) return 'give_up';                                     // A → B → A
  if (s.lastDiffSimilarity > 0.95) return 'give_up';                          // nem változott érdemben
  return 'continue';
}
```

- **`maxRounds` = 3** javítási kör (a P0 szabálya). Utána: interaktív módban őszinte jelzés a
  felhasználónak („ezt nem sikerült ellenőrizetten megoldanom; itt tartok: …”), éjjel feladás +
  kíváncsiság-kérdés a hiányzó tudásról ([03-onkerdezes.md](03-onkerdezes.md)).
- **Oszcilláció:** ha az n. javítás tartalma a hash vagy `textSimilar ≥ 0,95` alapján az (n−2).-kal
  egyezik, a vita körbe jár → megáll.
- **A Gondolkodó nem „hajol meg” bizonyíték nélkül:** ha egy kritikapont `evidence` nélküli vagy a
  tesztek cáfolják, a javításban `rejected: [{id, reason}]` mezővel elutasíthatja.

## 4. Szavazás és self-consistency

| Kimenet típusa | Módszer | Mikor |
|---|---|---|
| Rövid, diszkrét (A/B, „kell-e web?”, kategória) | k = 3 minta, `temperature` 0,7, többség; döntetlen → `bizonytalan` | interaktívan is (≤ 20 token/minta) |
| Terv (lépéslista) | k = 2–3 terv, a Kritikus pontozza ellenőrzőlistával | csak tétlenségben / éjjel |
| Kód | k jelölt, **a tesztek döntenek** (pass@k), nincs szavazás | éjjel, k ≤ 3 |
| Tényállítás | nem szavazunk: forrás-egyezés dönt ([../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md)) | — |

A szavazás ára **k × generálás**. Azonos promptra a cache-újrahasználat várható, de az Ollama 0.40
mért viselkedése mellett ezt **mérni kell**. A többségi szavazás a kis modell *véletlen* hibáit
szűri, a *rendszeres* tévedését nem — ezért tényekre és kódra külső ellenőrzés kell.

## 5. Költségkeretek CPU-n

Tipikus kimeneti hosszak és idők gemma4:e2b-n (**becslés** a mért ~6,2 tok/s-ből; az új kontextus
prefillje és a sandbox ideje erre jön rá, ezeket mérni kell):

| Lépés | Kimenet (token, becslés) | Idő (becslés) |
|---|---|---|
| Kérdező | ~80 | ~13 s |
| Javaslat (1 kis fájl) | ~300 | ~48 s |
| Kritika | ~120 | ~19 s |
| Javítás | ~300 | ~48 s |
| Tanulság-kártya | ~100 | ~16 s |

→ Egy teljes kör ~2–2,5 perc (becslés) még a leggyorsabb modellel is. Egy coder modell CPU-n ennél lassabb
lehet (becslés, nincs mérve). Ezért módonként más a keret:

| Mód | Mikor | Kör / szerep | Időkeret (kiinduló, hangolandó) |
|---|---|---|---|
| **interaktív** | a felhasználó vár | Kérdező csak kétértelműségnél; Kritikus csak nem egyértelmű hibánál; Tanár halasztva | ~120 s, utána részeredmény + jelzés |
| **tétlen** | a gép szabad, a felhasználó nem dolgozik | minden szerep, ≤ 3 kör | ~10 perc / feladat |
| **éjszakai** | ütemezett önálló tanulás (P4) | + szavazás, hideg kritika, pass@k | ~30 perc / feladat, éjszakai összkeret |

Ha a felhasználó közben aktív lesz, a háttérmunkamenet **megáll a következő lépéshatáron**, és az
átiratból később folytatható (egy Ollama-sáv, a felhasználó elsőbbsége).

## 6. Az átirat formátuma (JSONL, lépésenként egy sor)

```json
{"sid":"th_20261121_2215_a1","step":3,"role":"GONDOLKODO","model":"gemma4:e2b","mode":"tetlen","in_tok":412,"out_tok":288,"ms_first":610,"ms_total":47100,"out":{"approach":"…","files":[{"path":"slugify.py","sha256":"9f2c…"}]}}
{"sid":"th_20261121_2215_a1","step":4,"role":"SANDBOX","cmd":"pytest -q","exit":1,"summary":"2 failed: test_unicode, test_empty","ms_total":2300}
{"sid":"th_20261121_2215_a1","step":5,"role":"GONDOLKODO","kind":"revise","addresses":["T:test_unicode","T:test_empty"],"rejected":[],"out_tok":301}
{"sid":"th_20261121_2215_a1","step":6,"role":"SANDBOX","cmd":"pytest -q","exit":0,"summary":"6 passed"}
{"sid":"th_20261121_2215_a1","step":7,"role":"DONTES","verdict":"accept","reason":"tests_green","rounds":1}
```

(A számok példa-értékek.) A fájltartalmak nem az átiratban, hanem tartalom-hash alapján külön
tárolódnak (deduplikálva). Minden sor a mentés előtt átmegy a személyesadat-szűrőn (`isPersonal`
mintájára) — ami fennakad, az nem kerül az átiratba.

## 7. Mi marad meg?

| Mi | Hova (P1-től SQLite) | Meddig |
|---|---|---|
| Teljes, szűrt átirat | `thinking_log` | ~30 nap (kiinduló érték), utána csak az összesítő |
| Összesítő: szerepek, körök, idő, token, verdikt | mérési tábla | tartósan → [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) |
| Elfogadott megoldás + tesztjei | kódtudástár, `ellenőrzött` | tartósan |
| Tanulság-kártya | tudástár, ismétlési ütemezéssel | ld. [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md) |
| Általánosítható hibaminta (pl. „off-by-one a `range`-ben”) | tanulság-kártya, bizonyíték = a bukó teszt | tartósan |
| Elvetett javaslat, téves kritika | csak az átiratban | **nem** lesz tudás |
| Személyes adat | **sehova** | — |

A modell „gondolatmenete” önmagában soha nem tudás — csak az, amit az ellenőrzés igazolt.

## 8. Ismert hibamódok és ellenszerük

| Hibamód | Jel | Ellenszer |
|---|---|---|
| Kritikus hallucinál hibát | `evidence` hiányzik / a teszt cáfolja | bizonyíték nélküli pont nem számít |
| Gondolkodó mindent elfogad | jó kód elrontása egy téves pont miatt | `rejected` mező; regresszió esetén visszaállás az előző zöld változatra |
| Végtelen `minor` pontok | körszám nő, teszt zöld | `minor` soha nem indít új kört |
| Körbejárás | A → B → A | oszcilláció-detektor |
| Lassú háttérvita zavarja a felhasználót | aktivitás közben fut | megállás lépéshatáron, folytatás később |

## 9. Kész, ha

1. A P0-feladatkészleten a protokoll ≤ 3 körrel fut, és **minden** munkamenet `accept` / `give_up` /
   `ask_help` állapotban zárul (nincs lógó vita).
2. Az átirat minden lépése visszajátszható, és tartalmazza az időt/tokent → a költségtábla mért
   számokkal frissíthető.
3. Mérve: a Kritikus bevonása (P3) a P0-hoz képest javítja a sikerarányt — ha nem, interaktív módban
   kikapcsoljuk ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)).

## Kapcsolódó

- [01-szerepek.md](01-szerepek.md) · [03-onkerdezes.md](03-onkerdezes.md) · [04-prompt-sablonok.md](04-prompt-sablonok.md)
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) · [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md)
- [../07-komplex-feladatok/04-onellenorzes-es-javitas.md](../07-komplex-feladatok/04-onellenorzes-es-javitas.md)
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) — hol él az átirat
- [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) — az éjszakai mód keretei
