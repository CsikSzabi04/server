# Szerepek — kik „beszélgetnek” Auri fejében

> **Miről szól:** a belső párbeszéd szereplői (Kérdező, Gondolkodó/Javasló, Kritikus, Tesztelő,
> Tanár/Összefoglaló): mit kapnak, mit adnak vissza, és miért a mi gépünkön (CPU, egy Ollama-sáv)
> **egy modell szerep-címkékkel** az alapeset. A vita menete: [02-vita-protokoll.md](02-vita-protokoll.md).

## 1. Miért kellenek szerepek?

Egy kis modell egyetlen hívásban hajlamos magabiztosan hibázni. Ha ugyanazt a munkát **szűk
feladatokra** bontjuk (megért → javasol → tesztel → kritizál → összefoglal), minden lépés rövidebb,
ellenőrizhetőbb, és a hibák egy része kiderül, mielőtt a felhasználó látná. A szerep tehát nem „másik
személyiség”, hanem **egy szűk feladat + kötött kimeneti formátum (JSON)**.

A legerősebb kritikus nem modell, hanem a **valóság**: a fordító, a tesztfuttatás a sandboxban, a
források egyezése. A modell-szerepek ezek köré épülnek, nem helyettük.

## 2. Az öt szerep

| Szerep | Feladat | Bemenet | Kimenet (JSON) | A ciklus lépése |
|---|---|---|---|---|
| **Kérdező** | Mit kérnek valójában? Mit nem tudunk? Kell-e pontosító kérdés? | feladat + visszakeresett tudás | `subquestions`, `unknowns`, `ask_user` | 2. MEGÉRTÉS |
| **Gondolkodó / Javasló** | terv, kód, válaszvázlat | feladat + tudás + (tesztek) | `approach`, `steps`, `files[]`, `assumptions` | 3. TERV, 4. CSELEKVÉS |
| **Tesztelő** | teszteket ír a specifikációból (a kód előtt), értelmezi a sandbox kimenetét | feladat / nyers tesztkimenet | `tests[]` / `failing[]`, `next_action` | 3. és 5. |
| **Kritikus** | konkrét, bizonyítékkal alátámasztott hibák — **nem ír újra** | javaslat + ellenőrzési eredmény | `issues[]` súlyossággal, `verdict` | 5. ELLENŐRZÉS |
| **Tanár / Összefoglaló** | tanulság-kártya, magyarázat a felhasználónak | lezárt munkamenet | `lesson`, `card`, `explanation` | 7. TANULSÁG |

A **Döntés** szándékosan **nem** modell-szerep: szabályalapú kód (az `arbiter` mintájára) dönt a
kimenetekből — zöldek a tesztek? van blokkoló kritika? elfogyott a keret? Ld. [02-vita-protokoll.md](02-vita-protokoll.md).

Segéd-szerepek ugyanabban a szerepkönyvben (hogy a prefix közös maradjon): **Kivonatoló** (weboldalból
idézettel alátámasztott állítások) és **Választó** (szavazáshoz). A felhasználónak szóló végső
megfogalmazás (**Fogalmazó**) viszont a persona-munkamenetben fut. Sablonok: [04-prompt-sablonok.md](04-prompt-sablonok.md).

### Szerepenkénti szabályok

- **Kérdező:** max. 5 részkérdés, mindegyikhez megmondja, *honnan* jöhet a válasz (`store` / `sandbox`
  / `web` / `model` / `user`). A felhasználót legfeljebb **egy** kérdéssel zavarja. Részletek:
  [03-onkerdezes.md](03-onkerdezes.md).
- **Gondolkodó:** a feltevéseit kimondja (`assumptions`). Kódot csak **teljes fájlként** ad (nincs
  „… a többi változatlan”), hogy a sandbox futtatni tudja.
- **Tesztelő:** a tesztek a *specifikációt* ellenőrzik, nem a javaslat belső részleteit; legyen benne
  határeset és hibaág. A sandbox nyers kimenetét okokra bontva, röviden foglalja össze.
- **Kritikus:** csak `blocking` / `major` / `minor` súlyú, **helyhez kötött** (`where`) hibát írhat,
  **bizonyítékkal** (`evidence`: tesztkimenet, forrás, idézett sor). Ízlésbeli megjegyzés = `minor`,
  és az nem indít új kört. Ha nincs érdemi hiba: `issues: []`, `verdict: "accept"` — ez is jó eredmény.
- **Tanár:** csak abból tanít, ami **ellenőrzött** lett (zöld teszt, egyező források); ami nem, az
  `hipotézis` jelölést kap. Ld. [../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md](../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md).

## 3. Egy modell szerep-címkékkel, vagy több modell?

### A mért kényszerek ([../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md))

- **Egy Ollama-sáv:** a szerepek sorban futnak, valódi párhuzamosság nincs.
- **gemma4:e2b ~6,2 tok/s** → egy 150 tokenes kritika ~24 s (becslés a mért sebességből).
- **KV-cache:** csak egy korábbi prompt *végétől* folytatható; a rendszerprompt cseréje gemma4:e2b-n
  ~6 s, e4b-n ~17 s. Ha minden szerep saját rendszerpromptot kapna, **minden szerepváltás** ezt fizetné.

### Az alapeset: egy modell, egy közös „szerepkönyv”, a szerep a felhasználói üzenetben

```
[system]  SZEREPKÖNYV: Auri belső munkamenete, az 5 szerep leírása, JSON-szabályok   ← bájtra stabil
[user]    <szerep>KERDEZO</szerep><feladat>…</feladat><tudas>…</tudas>
[asst]    {"subquestions":[…],"unknowns":[…],"ask_user":null}
[user]    <szerep>GONDOLKODO</szerep><tesztek>…</tesztek>                                 ← csak hozzáfűzés
[asst]    {"approach":"…","files":[…]}
[user]    <szerep>KRITIKUS</szerep><ellenorzes>pytest: 2 failed …</ellenorzes>
[asst]    {"issues":[…],"verdict":"revise"}
```

A munkamenet **csak hozzáfűzve** nő (mint a Jarvis `auri_jarvis/mind/prompts.py` `build_messages`-e),
így minden új kérés az előző prompt végétől folytatja a cache-t, és csak az új rész prefilljét
fizetjük (a prefill sebességét CPU-n **mérni kell**). A szerepkönyv szövege:
[04-prompt-sablonok.md](04-prompt-sablonok.md) (T0).

### Döntési tábla

| Helyzet | Javaslat | Indok |
|---|---|---|
| A felhasználó vár (interaktív) | **1 modell**, szerep-címkék, max. 1 kritika-kör | idő; nincs prefixváltás |
| Kódírás, ha van telepített coder modell (P6) | Gondolkodó **és** Kritikus is a coder modell | a modellcsere drágább, mint a kisebb diverzitás |
| Éjszakai tanulás (P4) | több modell is lehet, de **modellenként kötegelve** | egy betöltés sok feladatra oszlik el |
| A Kritikus ugyanazt a vakfoltot látja (2× ugyanaz a hibás javítás) | második vélemény más modelltől éjjel, vagy felhő (P6, opt-in) | diverzitás kell, de ritkán |
| Rövid diszkrét döntés (A/B, osztályozás) | 1 modell, k = 3 minta, többségi szavazás | olcsó, ha a kimenet ≤ 20 token |

A **modellcsere** (kirakás + betöltés) ideje nincs a tények között → **mérni kell**, és fel kell
venni a tényekhez. 16 GB RAM mellett egy coder modell (pl. `qwen2.5-coder:14b`, ~9 GB Q4, becslés) mellé
nem fér kényelmesen egy második közepes modell — ez is az egy-modelles alapesetet támogatja.

### Az „önkritika” csapdája

Közös munkamenetben a Kritikus a *saját* korábbi szövegét bírálja; a kis modellek ilyenkor
engedékenyek. Ellenszerek:
1. **Előbb a determinisztikus ellenőrzés** (fordítás, teszt, lint), a Kritikus már ennek eredményét kapja.
2. **Ellenőrzőlista + kötelező bizonyíték** (`evidence`) — bizonyíték nélküli hiba nem számít.
3. **„Hideg kritika”** éjjel: új munkamenet, csak a feladat + a végső javaslat; egyszeri prefix-ár.

## 4. Szerepek a fázisokban

| Fázis | Szerepek | Megjegyzés |
|---|---|---|
| P0 | Gondolkodó + sandbox (Tesztelő helyett a kész tesztek) + Döntés | a „kritika” = a tesztkimenet; ≤ 3 javítási kör |
| P1 | ugyanaz, az Auri Core-ban | a munkamenet-napló SQLite-ba kerül |
| P3 | mind az öt | a teljes vita-protokoll |
| P4 | Kérdező + Tanár éjszakai módban | kíváncsiság-sor, teach-back |
| P5 | Gondolkodó részfeladatonként, Kritikus a terven is | [../07-komplex-feladatok/01-feladatbontas.md](../07-komplex-feladatok/01-feladatbontas.md) |

## 5. Implementációs vázlat

```ts
type Role = 'KERDEZO' | 'GONDOLKODO' | 'TESZTELO' | 'KRITIKUS' | 'TANAR';

interface RoleSpec {
  role: Role;
  schema: object;        // JSON-séma → Ollama `format` (kötött kimenet)
  maxTokens: number;     // num_predict — CPU-n a kimenet hossza maga a költség
  temperature: number;   // kiinduló érték (hangolni kell): Gondolkodó 0.4, a többi 0.2–0.3
}

interface ThinkingSession {
  id: string;
  model: string;         // a munkamenet alatt NEM változik
  system: string;        // a szerepkönyv — bájtra azonos minden körben
  messages: ChatMsg[];   // csak hozzáfűzés; korábbi kört soha nem írunk át
  budget: { msLeft: number; turnsLeft: number; outTokensLeft: number };
}
```

## 6. Kész, ha

1. A szerepkönyv egyetlen stabil rendszerprompt, és egy 5 lépéses munkamenetben **nincs prefixváltás**
   (mérve: a 2.+ kérés első tokenje nem ugrik fel a ~6 s-os prefixváltási szintre).
2. Mind az öt szerep érvényes JSON-t ad a [04-prompt-sablonok.md](04-prompt-sablonok.md) sémáival a
   próbafeladatok ≥ 95%-án (célérték, mérni kell).
3. A Kritikus `accept`-et ad, ha nincs bizonyítható hiba (nem talál ki hibát) — ellenőrizve egy
   10 hibátlan + 10 hibás megoldásból álló készleten ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)).

## Kapcsolódó

- [02-vita-protokoll.md](02-vita-protokoll.md) · [03-onkerdezes.md](03-onkerdezes.md) · [04-prompt-sablonok.md](04-prompt-sablonok.md)
- [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) — a ciklus, amibe a szerepek illeszkednek
- [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) — Tesztelő a kód előtt
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) · [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md)
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
