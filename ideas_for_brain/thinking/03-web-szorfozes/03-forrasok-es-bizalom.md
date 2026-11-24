# Források és bizalom — mennyire higgyünk egy oldalnak?

> **Miről szól:** a bizalmi pontszám felépítése (forrás típusa, frissesség, források egyezése,
> futtatással igazolás), a tudás állapotai (hipotézis → valószínű → ellenőrzött), az ellentmondások
> kezelése, és hogyan jelenik meg mindez a válaszban. A meglévő `web/src/autolearn/trust.ts`-re épül.

## 1. Miért kell?

A kis modell nem tudja megkülönböztetni a hivatalos dokumentációt egy elavult blogtól. A bizalmi
pontszám dönti el, hogy (1) melyik találat kerül előre, (2) mi kerülhet a tudástárba, (3) mit kell még
ellenőrizni, és (4) mit mondunk ki bizonytalanként. Alapelv: **a futtatással igazolt tudás erősebb
bármilyen forrásnál** — egy forrás csak azt mondja meg, mit érdemes kipróbálni.

## 2. Forrás-osztályok (kezdő bizalom)

| Osztály | Példa | Kezdő érték (kiinduló, kalibrálandó) | Mai kód |
|---|---|---|---|
| **A** hivatalos doku, nyelvi specifikáció, RFC | MDN, docs.python.org, nodejs.org, react.dev, rfc-editor.org | 0,90 | `domainTrust` = 1 (HIGH lista) |
| **B** a könyvtár saját repója (README, CHANGELOG, forráskód) | `github.com/<szervezet>/<repo>`, ha a csomag hivatalos repója | 0,85 | `domainTrust` 0,65 (MED: github.com) → pontosítani |
| **C** Q&A elfogadott / magas pontszámú válasz | Stack Overflow | 0,70 (alacsony pontszám: 0,50) | MED 0,65, `devTrust` bónusz |
| **D** ismert szakmai oldalak | baeldung, digitalocean, freecodecamp, css-tricks | 0,60 | MED 0,65 |
| **E** ismeretlen blog, közösségi cikk | Medium, dev.to, egyéni blogok | 0,40 | 0,4 |
| **F** tartalomfarm, SEO-szemét, gépi újraközlés | másolt Q&A-tükrök | 0,10 (szürkelista) | — (új) |

A mai `domainTrust` (1 / 0,65 / 0,4 / 0,3) a **domain** szintjén dönt; az új réteg az **oldal típusát**
is nézi (`PageDoc.kind`, [02-oldalolvasas.md](02-oldalolvasas.md)): ugyanazon a `github.com`-on a
hivatalos repó README-je B, egy véletlen fork A-hoz képest E.

## 3. A pontszám

```ts
interface TrustInput {
  cls: 'A'|'B'|'C'|'D'|'E'|'F';
  ageDays: number; ttlDays: number;
  versionMatch: 'yes'|'no'|'unknown';   // a kártya appliesTo vs. a projekt verziója
  independentAgreeing: number;          // független egyező források száma (önmagán kívül)
  contradictedByHigher: boolean;        // magasabb osztályú forrás ellentmond
  sandbox: 'passed'|'failed'|'not_run';
  suspicious: boolean;                  // injekció-gyanú az oldalon
}

function trust(t: TrustInput): number {
  let s = PRIOR[t.cls];                                        // 2. pont táblázata
  if (t.ageDays > t.ttlDays) s *= 0.7;                         // elavult
  if (t.versionMatch === 'no') s *= 0.5;
  s += Math.min(0.15, 0.08 * t.independentAgreeing);           // egyezés bónusz, plafonnal
  if (t.contradictedByHigher) s -= 0.3;
  if (t.sandbox === 'passed') s = Math.max(s, 0.9);            // a valóság felülír
  if (t.sandbox === 'failed') s = Math.min(s, 0.2);
  if (t.suspicious) s = Math.min(s, 0.2);
  return Math.max(0, Math.min(1, s));
}
```

Az együtthatók **kiinduló becslések**; a kalibrálás módja: egy kézzel címkézett állításkészleten
(igaz/hamis) megnézzük, hogy a pontszám-sávok mennyire egyeznek a valós helyességgel
([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)).

### Állapotok (ez megy a tudáskártyára)

| Állapot | Feltétel | Használat |
|---|---|---|
| `hipotézis` | pontszám < 0,4, vagy csak modell-állítás | nem idézzük tényként; kíváncsiság-sorba kerülhet |
| `valószínű` | 0,4–0,75, vagy egyetlen A/B forrás | válaszban „egy forrás szerint …” |
| `ellenőrzött` | **kód:** sandboxban lefutott a teszttel · **tény:** ≥ 2 független forrás egyezik, ebből ≥ 1 A vagy B osztályú | szabadon használható, a router előnyben részesíti |
| `vitatott` | magas bizalmú források ellentmondanak | mindkét változat megmarad, megjegyzéssel |

## 4. Frissesség (TTL)

Ma: `ttlDaysForQuery` — változékony kulcsszó (ár, hír, verzió, release, évszám) → 3 nap, egyébként
180 nap; `isStale(fetchedAt, ttlDays)`. Ez a **lekérdezést** nézi; a kártyáknál a **tartalom típusa**
pontosabb:

| Kártyatípus | TTL (kiinduló) | Megjegyzés |
|---|---|---|
| Nyelvi alapfogalom (pl. mi a closure) | 365 nap | ritkán változik |
| Könyvtár-API, CLI-kapcsoló | 90 nap **és** verzióhoz kötve (`appliesTo`) | verzióváltáskor azonnal újraellenőrzendő |
| „Legújabb verzió”, kiadási dátum | 3 nap | a mai VOLATILE szabály |
| Hibamegoldás (hibaüzenet → javítás) | 180 nap, verzióhoz kötve | — |

Lejárt kártya **nem törlődik**, hanem `újraellenőrzendő` lesz, és az éjszakai tanulás sorra veszi
([../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md)).

## 5. Források egyezése

- **Független-e?** Két forrás csak akkor számít külön, ha más a domainje **és** a szövegük nem
  másolat (`textSimilar` < 0,82, a `dedup.ts` küszöbe). A Q&A-tükrök és újraközlők nem erősítenek.
- **Állítás-szintű összevetés:** a Kivonatoló idézettel alátámasztott állításokat ad
  ([04-tanulas-a-webbol.md](04-tanulas-a-webbol.md)); a normalizált állítás (alany + API-név + verzió)
  a kulcs.
- **Ellentmondás esetén:**

| Eset | Döntés |
|---|---|
| A vagy B osztály vs. E/F | a magasabb nyer; az alacsonyabbról megjegyzés („elavult/hibás forrás”) |
| Két A-forrás eltér | szinte mindig **verziókülönbség** → `appliesTo` szétválasztja őket |
| Futtatással eldönthető | a sandbox dönt (ez a leggyakoribb a programozásban) |
| Nem dönthető el | `vitatott`; mindkettő megmarad; kíváncsiság-kérdés születik |

## 6. Felülbírálás

A felhasználó (vagy a fejlesztő) kézzel is állíthat: helyi konfigurációs fájl, pl.

```yaml
# trust_overrides.yaml — a domain-szintű alapértékek felülírása
boost:   { "fastapi.tiangolo.com": A, "docs.pydantic.dev": A }
grey:    { "example-content-farm.com": F }
block:   [ "malware-sample.example" ]   # soha nem töltjük le
```

## 7. Megjelenés a válaszban

Minden webes eredetű állításnál a forrás linkje, és egy rövid, magyar bizonyosság-jelző:
„ellenőrizve (lefuttattam)” · „két független forrás szerint” · „egy forrás szerint” · „bizonytalan —
nem tudtam ellenőrizni”. Hangmódban csak a jelző hangzik el, a link a felületen jelenik meg.

## 8. Kész, ha

1. Minden tudáskártyán van `trust`, `state`, `sources[]`, `fetchedAt`, `ttlDays` — enélkül nem menthető.
2. Egy 50 állításból álló címkézett készleten az `ellenőrzött` kártyák ≥ 95%-a igaz, a `hipotézis`
   sávban érezhetően több a hamis (célértékek, mérni kell) — azaz a pontszám **jelent** valamit.
3. A verzióhoz kötött kártya a projekt függőségének váltásakor `újraellenőrzendő` lesz.

## Kapcsolódó

- [01-kereses.md](01-kereses.md) · [02-oldalolvasas.md](02-oldalolvasas.md) · [04-tanulas-a-webbol.md](04-tanulas-a-webbol.md)
- [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) — hol élnek a kártyák
- [../00-alapok/04-fogalomtar.md](../00-alapok/04-fogalomtar.md) — hipotézis / ellenőrzött tudás
