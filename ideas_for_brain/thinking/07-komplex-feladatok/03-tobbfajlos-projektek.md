# Többfájlos projektek — váz, szerződés, fájl-tulajdon, integráció

> **Miről szól:** hogyan épít Auri több fájlból álló projektet úgy, hogy a fájlok illeszkedjenek, pedig
> egyszerre mindig csak egyet lát. A minta valódi: ennek a repónak a „3 AI-s” építése (`JARVIS_BUILD.md`
> 0–3. szakasz) — itt általánosítjuk egyetlen kis modell soros munkájára.

## 1. Miért nehéz ez egy kis modellnek

- **Nem fér el minden a kontextusban:** CPU-n a hosszú prompt drága, és a modell a hosszú kontextus
  közepét amúgy is rosszul használja (becslés, kis modelleknél tapasztalati).
- **Illesztési hibák:** rossz importútvonal, eltérő mezőnév (`done` vs. `completed`), kitalált függvény.
- **Hiba-továbbterjedés:** ha az alsó réteg rossz, minden ráépülő fájl is az lesz.

A megoldás nem „több kontextus”, hanem **fegyelem**: közös szerződés, egy fájl — egy író, csonkok
(fake-ek), rétegenkénti kapuk. Pontosan ezt csinálta a Jarvis-építés.

## 2. A precedens: hogyan működött a `JARVIS_BUILD.md`

Három erős (felhős) AI dolgozott párhuzamosan, ember koordinálásával. Ami bevált (0–3. és 6–7. szakasz):

| JARVIS_BUILD szabály | Mire volt jó | Auri belső megfelelője |
|---|---|---|
| §0.1 / §1: mindenki **csak a saját zónáját** szerkeszti | nulla ütközés | **fájl-tulajdon**: egy fájlt egyetlen feladat ír (`Task.writes`) |
| §0.2: függőséget **csak az AI-3** telepít | egy kézben a környezet | csomaglistát csak az **Integrátor** feladat módosít, csak engedélylistáról |
| §0.4 + §2.1: `contracts.py` **szó szerint, elsőként**; a többiek importálnak | közös nyelv, a többiek „nem várnak rá” | a `contract` feladat fut elsőként, utána **befagyasztva** (hash) |
| `fakes.py` (pl. `EchoMind`, fake fül/száj) | mindenki tesztelhet a többiek nélkül | a szerződésből **csonk/fake** készül → a feladat tesztje a függőség kész kódja nélkül is fut |
| §3: mérföldkövek „Kész, ha” oszloppal, az AI-3 ellenőrzi | mérhető átadás | **mérföldkő-kapu** gépi checkekkel, az Integrátor futtatja |
| §4: append-only státusz-log | kommunikáció + visszakereshetőség | **futási napló** (JSONL), ebből készül a jelentés |
| §6: integrációs sor — közös fájl / szerződés csak kéréssel | kontrollált változás | `contract.change_request` → újratervezés ([02](02-terv-vegrehajtas-ellenorzes.md)) |
| §7: közös minőségkapuk (tesztek, selftest, biztonsági tesztek, számok) | egységes minőség | **záró kapu**: összes teszt + smoke + őr + mért idők |
| §0.9: „mérj, ne higgy” | állítás csak számmal | a jelentés minden állítása a naplóra mutat |
| §0.12: bizonytalan határnál ne nyúlj hozzá, kérdezz | ne rontsd el másét | `NeedsUser` → kérdés a felhasználónak ([04](04-onellenorzes-es-javitas.md)) |

Ugyanez a minta a BRAIN-építésnél is működött: `web/src/brain/contracts.ts` — „pure types, no runtime
logic”, egy tulajdonos, a többiek csak importálnak.

**A lényeges különbség:** ott a fegyelem a **párhuzamosságot** szolgálta; Auri egy sávon, sorban
dolgozik. Nála ugyanez a fegyelem a **kontextus szűkítését** és a **hiba helyhez kötését** szolgálja:
minden lépés csak a szerződést, a saját fájlját, a saját tesztjét és a függőségei aláírását látja.

## 3. A projekt-manifeszt

```ts
type FileRole = 'contract' | 'impl' | 'test' | 'fake' | 'config' | 'doc';
interface ProjectFile {
  path: string;
  role: FileRole;
  owner: string;                 // Task.id | 'scaffold' | 'integrator'
  frozen: boolean;               // szerződés: a saját feladata után; teszt: a kód-feladat alatt
  sha: string;
  exports?: string[];            // repo-térkép: "export function createApp(repo): Express"
}
interface ProjectManifest {
  name: string;
  kind: 'python' | 'node' | 'react' | 'js' | 'java';  // ugyanaz, mint a web/src/lib/codeProjects.ts ProjectKind-ja
  runtime: { node?: string; python?: string };         // pl. node 24.14.0 (a gépen ellenőrizve)
  deps: { name: string; version: string }[];           // csak engedélylistáról, csak az Integrátor írja
  commands: { test: string; smoke?: string; start?: string };
  files: ProjectFile[];
}
```

## 4. Az építés sorrendje

1. **Váz (scaffold), 0 LLM.** Sablonból: a `web/src/lib/codeProjects.ts` `scaffold()` függvénye már ad
   indulófájlokat (python / node / react / js / java) — ezt bővítjük **tesztfuttatóval** (node:
   `"test": "node --test"`, python: `unittest`), `.gitignore`-ral és a manifeszttel. A sablonok a
   kódtudástárban receptként élnek.
2. **Szerződés** (`contract`): típusok, modulhatárok aláírásai, API-séma, hibaforma → befagyasztás.
3. **Csonkok** (`fake`), lehetőleg determinisztikusan generálva a szerződésből (pl. memóriabeli repo).
4. **Tesztek** rétegenként (`test` feladatok) — piros állapot ellenőrzése: a teszt **lefut és elbukik**,
   de nem szintaxishiba miatt.
5. **Implementáció alulról felfelé:** tiszta logika → tárolás → HTTP/UI → összekötés (`server.js`, `main.py`).
6. **Integráció:** a csonkok helyére a valódi modulok, integrációs tesztek, smoke.

## 5. Mit lát egy fájl-feladat? (kontextus-csomagolás)

| Mindig | Ha van | Soha |
|---|---|---|
| a feladat 1–3 mondatos leírása | recept-részlet ugyanerre a fájltípusra | más fájlok teljes implementációja |
| a szerződés (teljes) | max. 2 találat a kódtudástárból (ellenőrzött) | a teljes repó |
| a fájl saját tesztje | stílus-tipp: a `learningsPrompt(kind)` kimenete (`codeProjects.ts`) | személyes adat, titok, `.env` |
| az importált modulok **aláírásai** (repo-térkép) | az utolsó hibakivonat (javító módban) | korábbi sikertelen próbák teljes szövege |

Keret: ≤ ~2500 token bemenet (**becslés**, a P0 után hangolva). A **repo-térkép** determinisztikusan
készül (JS: export-sorok regexszel vagy parserrel; Python: `ast`), LLM nélkül — minden checkpoint után frissül.

## 6. A tulajdon szabályai

- Egy fájlt egy feladat ír; a többi feladat számára **csak olvasható**.
- Ha egy feladatnak más fájlját kellene módosítania, **nem teszi**: `edit` kérés kerül a naplóba, és a
  tervező új `edit` feladatot vesz fel (az eredeti írótól függ, a módosítás mérete korlátozott, a régi
  tesztek regresszióként futnak).
- A tesztfájl a kód-feladat alatt **befagyasztott** — a kód igazodik a teszthez, nem fordítva.
- Csomagfüggőséget csak az Integrátor vesz fel, csak engedélylistáról, és csak előre letöltött cache-ből;
  csomagot használó, többfájlos (L3–L4) kód **csak S1 sandboxban** fut, hálózat nélkül ([../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md)).
- A végén a napló alapján ellenőrizzük: **egyetlen** fájlt sem írt olyan feladat, aki nem tulajdonosa.

## 7. Integrációs tesztek

| Szint | Mit bizonyít | Példa (todo API) |
|---|---|---|
| Szerződés-teszt | az implementáció a szerződést követi | minden `ROUTES` elem válaszol, a hibaforma egyezik |
| Rétegközi | a valódi modulok együtt működnek | `createApp(createRepo(':memory:'))` + HTTP-hívások |
| Smoke | a program elindul | `node src/server.js` → `GET /health` = 200, 5 s-on belül, csak loopbacken |
| Regresszió | semmi nem romlott el | a teljes `npm test` minden mérföldkő végén |

## 8. Kész, ha

- Egy 3 fájlos és egy 6–8 fájlos mintaprojekt emberi beavatkozás nélkül zöldre fut, és a manifeszt
  minden fájl tulajdonosát, hash-ét, szerepét helyesen mutatja.
- A napló szerint egyetlen feladat sem írt idegen fájlt, és a szerződés hash-e csak `change_request` után változott.
- Egy szándékosan elrontott import (illesztési hiba) a rétegközi teszten bukik meg, és a javítás a hibás fájlra korlátozódik.
- A fájl-feladatok bemenetének mediánja (a naplóból mérve) az 5. pont keretén belül marad.

## Kapcsolódó

- [01-feladatbontas.md](01-feladatbontas.md) · [02-terv-vegrehajtas-ellenorzes.md](02-terv-vegrehajtas-ellenorzes.md) · [05-teljes-pelda.md](05-teljes-pelda.md)
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) — sablonok, receptek, repo-térkép
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) — csomag-cache, hálózat nélküli futtatás
- [../06-programozas/07-sajat-projektekbol-tanulas.md](../06-programozas/07-sajat-projektekbol-tanulas.md) — a `codeProjects.ts` tanulságai
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md)
