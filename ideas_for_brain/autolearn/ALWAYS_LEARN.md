# „Mindig tanulj a webről" — 1 soros bekötés AI-3-nak

> A user kérése: **minden üzenetnél keresse a linkeket és mentse el az ott talált fontos adatokat/
> szavakat** — akkor is, ha az agy már tudja a választ. A **motor kész és típus-ellenőrzött** az én
> zónámban (`autolearn/backgroundLearn.ts`); a „minden üzenetnél süljön el" **trigger az App.tsx
> send-jében van (AI-3 zónája)**, ezért ezt **AI-3 köti be** — 1 import + 1 sor, fire-and-forget.

## Mit csinál (biztonsági fékekkel)
`alwaysLearn(query, { search, ingest })` minden érdemi kérdésnél a **háttérben** keres és **beadja az
agyba** a fontos találatokat — de:
- **triviális-szűrés:** köszönés / „ok" / kevés kulcsszó → nem keres (`minKeywords`, alap 2),
- **cache:** ugyanarra a témára nem keres újra (`searchCache`, 6h),
- **rate-limit:** token-bucket (12/perc) → a kulcs nélküli DDG nem hammerelődik,
- **dedupe + rerank:** csak a legjobb, deduppolt találatok mennek be (forrás-bizalom szerint),
- **soha nem dob hibát** (fire-and-forget biztonságos).

Visszaad: `{ searched, hits, terms, reason }` — a `terms` a találatokból kinyert **fontos ÚJ szavak**
(amik nem voltak a kérdésben) → AI-2 ki tudja rakni „learned: …" chipként a `/brain`-en.

## A bekötés (App.tsx `send`, a meglévő válasz-ág MELLÉ, nem helyette)
```ts
import { alwaysLearn } from '../autolearn';

// …a send()-ben, amint megvan a user `text`-je (NE await-eld — háttérben fusson):
void alwaysLearn(text, { search: searchWeb, ingest: brainChat.learnWebHits });
```

- `searchWeb` a meglévő `askPipeline`-ból (már az autolearn-tisztítást használja),
  `brainChat.learnWebHits` a meglévő tároló (→ AI-1 `learnWeb` → `region:web` doc + vocab/Markov).
- **Független a válasz-úttól:** a chat ugyanúgy brain-first → web → model; ez CSAK a háttér-tanulás,
  ezért minden körben nő az agy, akkor is, ha a választ az agyból/modellből adta.
- **Flag-javaslat:** tedd egy `auri.brain.alwaysLearn` kapcsoló mögé (alap BE), hogy ki lehessen
  kapcsolni — mert „mindig keres" több web-hívást jelent (a rate-limit/cache tcompenzál).

## Őszinte megjegyzés
A „mindig keres" **több külső kérés** (akkor is, ha az agy tudná a választ) → ezért fontos a
rate-limit + cache + triviális-szűrés, ami mind bent van. Privát adat nem megy ki: a `redactForSearch`
kiszedi az e-mailt/telefont/nevet a keresőkérésből. Lokális Ollaménál a chat a gépen marad, de a
**keresés mindig külső** (DDG) — ezt érdemes a UI-ban jelezni (pl. „🌐 háttér-tanulás BE").
