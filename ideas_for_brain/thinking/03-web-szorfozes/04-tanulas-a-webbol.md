# Tanulás a webből — oldalból ellenőrzött tudáskártya

> **Miről szól:** hogyan lesz egy elolvasott oldalból **kevés, ellenőrzött, újrahasználható tudás**:
> állítások idézettel, kódrészletek lefuttatva, forrással és bizalommal tárolva, duplikátumok nélkül.
> A mai `ingestWeb` / `distillFromModel` utódja.

## 1. Honnan indulunk

| Ma (`web/src/brain/web.ts`, `distill.ts`) | Probléma | Új |
|---|---|---|
| `ingestWeb`: a top találatok **snippetje** `WebDoc`-ként, súly a `domainTrust` alapján, + `observe` (szókincs/Markov) | a snippet nem tudás, a Markov-gráf nem érti | **tudáskártya**: állítás + idézet + forrás |
| `pages[]` teljes szövege `observe`-ba megy | kódblokkok elvesznek; ellenőrzés nincs | szakaszok + kódblokkok ([02-oldalolvasas.md](02-oldalolvasas.md)) |
| `distillFromModel`: a modell válasza ellenőrzés nélkül Q→A párrá válik | a modell tévedése „tudássá” lesz | modell-állítás csak `hipotézis` |

## 2. Kártyatípusok

| Típus | Mi van benne | Ellenőrzés |
|---|---|---|
| `fact` | egy mondatos állítás | források egyezése |
| `api` | szignatúra, paraméterek, visszatérési érték, verziótartomány | futtatás (import + hívás) |
| `snippet` | futtatható kódrészlet + elvárt kimenet | futtatás tesztként |
| `fix` | hibaüzenet → ok → javítás | a hiba reprodukálása, majd a javítás után zöld |
| `concept` | fogalom-magyarázat (HU + EN) | források egyezése, teach-back ([../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md](../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md)) |

```ts
interface KnowledgeCard {
  id: string; kind: 'fact'|'api'|'snippet'|'fix'|'concept';
  key: string;                         // kanonikus kulcs, pl. "python:str.removeprefix"
  claim_en: string; claim_hu?: string;
  code?: { lang: string; code: string; expected?: string };
  appliesTo?: { pkg: string; range: string };                   // pl. { pkg: "python", range: ">=3.9" }
  sources: { url: string; title: string; quote: string; fetchedAt: string; contentHash: string; license?: string }[];
  verification: { kind: 'sandbox'|'sources'|'none'; result: 'passed'|'failed'|'not_run'; env?: string; at?: string };
  trust: number; state: 'hipotézis'|'valószínű'|'ellenőrzött'|'vitatott'|'újraellenőrzendő';
  ttlDays: number; createdAt: string; updatedAt: string;
}
```

## 3. A csővezeték

```
PageDoc ─▶ 1. releváns szakaszok (keySentences / rerankSmart, a kérdéshez)
        ─▶ 2. kivonatolás (Kivonatoló, T9: állítás + SZÓ SZERINTI idézet, max. 6 / szakasz)
        ─▶ 3. idézet-ellenőrzés (kód): az idézet tényleg szerepel az oldalszövegben?
        ─▶ 4. kódellenőrzés a sandboxban (snippet / api / fix)
        ─▶ 5. bizalom + állapot (03-forrasok-es-bizalom.md)
        ─▶ 6. személyesadat-szűrés · duplikátum-keresés · összevonás
        ─▶ 7. tárolás provenance-szel ─▶ 8. ütemezett újraellenőrzés (TTL)
```

**3. Idézet-ellenőrzés** — a legolcsóbb hallucináció-szűrő: whitespace- és idézőjel-normalizálás után
az idézetnek részszövegként szerepelnie kell a szakaszban. Ha nincs meg → az állítás eldobva (nem
„javítjuk”). A kódot ugyanígy: a `code` mezőnek szó szerint egyeznie kell egy kinyert kódblokkal (a
futtatáshoz szükséges keret — importok, `print` — külön, jelölt kiegészítés lehet).

**2. Költség:** a Kivonatoló hívás szakaszonként ~150–250 token kimenet (becslés) → gemma4:e2b-n
~25–40 s. Ezért interaktívan csak az 1. lépés (extraktív, modell nélkül) fut, a modell-kivonatolás
**tétlenségben vagy éjjel** — a nyers szakaszok addig egy várakozó sorban állnak.

## 4. Kódrészletek ellenőrzése

1. **Nyelv és környezet** a kódblokk jelöléséből; a sandbox előre telepített futtatókörnyezetei
   (pl. Python, Node) közül választ. Hálózat nincs → a hálózatot igénylő snippet `not_run`.
2. **Teszt az állításból:** a Tesztelő (T2) vagy egy sablon a `expected` kimenetből assertiont ír,
   pl. `assert "TestHook".removeprefix("Test") == "Hook"`.
3. **Futtatás** időkorláttal ([../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md)); az `env`
   rögzíti a futtatókörnyezet verzióját.
4. **Eredmény:**

| Eredmény | Teendő |
|---|---|
| zöld | `verification.result = passed` → `ellenőrzött` (ha az idézet-ellenőrzés is rendben) |
| hiányzó csomag | `not_run` + kíváncsiság-kérdés; csomagot a sandbox **nem** tölt le magától |
| piros, verziókülönbség gyanúja | más verzióval újra, ha van; különben `appliesTo` szűkítése |
| piros, ok ismeretlen | `failed` → a kártya `hipotézis`; ha a forrás A/B osztályú, `vitatott` + jegyzet |

A hibás snippet is tanulság lehet: „a(z) X oldalon lévő minta Python 3.12-n nem fut” — `fix`-típusú
figyelmeztető kártya, ha általánosítható.

## 5. Duplikátumok és összevonás

- **Kanonikus kulcs** (`key`): nyelv/csomag + API-név vagy normalizált téma.
- **Hasonlóság:** azonos kulcs, vagy `textSimilar(claim) ≥ 0,82` (a `dedup.ts` küszöbe); később
  `embeddinggemma`-vektorok koszinusz-hasonlósága (küszöb mérendő).
- **Összevonáskor:** a forrás bekerül a `sources[]`-be (ha független, nő a bizalom), a jobb kód marad
  (ellenőrzött > rövidebb > magasabb bizalmú), a `claim` a legmagasabb bizalmú forrásé.
- Ugyanaz az URL változatlan `contentHash`-sel nem dolgozódik fel újra.

## 6. Licenc, mérték, adatvédelem

- **Rövid kivonat + link**, nem teljes oldal. A kódrészlet a forrás licencével együtt tárolódik
  (`license`); ismeretlen vagy nem engedélyező licencű kód nem kerül a kódtudástárba, csak a
  hivatkozása ([../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md)).
- CC BY-SA forrásoknál (pl. Stack Overflow) a forrás-URL a hivatkozás alapja; hogy a szerző nevét
  tároljuk-e, nyitott kérdés (a név személyes adat is lehet) — ld. [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md).
- Minden kártya mentés előtt átmegy a személyesadat-szűrőn (`isPersonal` mintájára); a fennakadó
  rész kitakarva vagy a kártya eldobva.

## 7. Példa

Kérdés: *„Hogyan vágok le egy előtagot egy stringről Pythonban?”*
1. Keresés → `docs.python.org` (A) és egy Stack Overflow-válasz (C).
2. Kivonatoló: `api` állítás „`str.removeprefix(prefix)` … New in version 3.9” + idézet; a SO-ból
   alternatíva: `s[len(p):] if s.startswith(p) else s`.
3. Idézet-ellenőrzés rendben. Sandbox: `assert "TestHook".removeprefix("Test") == "Hook"` → zöld.
4. Kártya: `key = python:str.removeprefix`, `appliesTo = python >=3.9`, `state = ellenőrzött`;
   a régi Pythonra érvényes alternatíva külön `snippet` kártya, `appliesTo = python <3.9`.
5. Legközelebb a kérdésre a tudástár válaszol, web nélkül, forrással.

## 8. Kész, ha

1. Egyetlen kártya sem kerül a tárba idézet vagy forrás nélkül (sémaszintű kényszer).
2. Egy 20 doku-oldalas próbán a kivonatolt állítások ≥ 90%-a átmegy az idézet-ellenőrzésen, a kódos
   kártyák ≥ 70%-a `ellenőrzött` lesz (célértékek, mérni kell).
3. Ugyanazt az oldalt kétszer feldolgozva nem keletkezik új kártya, csak a `updatedAt` változik.
4. A `distillFromModel` kimenete legfeljebb `hipotézis` állapotú lehet.

## Kapcsolódó

- [01-kereses.md](01-kereses.md) · [02-oldalolvasas.md](02-oldalolvasas.md) · [03-forrasok-es-bizalom.md](03-forrasok-es-bizalom.md)
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) · [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md)
- [../05-tanulas/01-tanulasi-forrasok.md](../05-tanulas/01-tanulasi-forrasok.md) · [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md)
- [../02-belso-parbeszed/04-prompt-sablonok.md](../02-belso-parbeszed/04-prompt-sablonok.md) (T9 Kivonatoló)
