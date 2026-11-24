# Oldalolvasás — „szörfözés” kerettel, nem tömeges letöltés

> **Miről szól:** hogyan olvas Auri weboldalt: biztonságos letöltés, a fő tartalom és a **kódblokkok**
> kinyerése, linkek követése mélység- és oldalkerettel, dokumentációs oldalak külön kezelése,
> robots.txt és felhasználási feltételek, valamint az, hogy a lap tartalma **adat, nem utasítás**.

## 1. Mit jelent itt a szörfözés?

Célzott olvasást egy **kérdés** mentén: a keresés ([01-kereses.md](01-kereses.md)) ad néhány URL-t,
Auri elolvassa a legjobbakat, és ha a válasz egy linkkel arrébb van (pl. a doku következő oldala),
**kereten belül** továbbmegy. Nem crawler: nem tölt le oldalakat „hátha jó lesz”, nem tükröz
webhelyeket, nem kerül meg bejelentkezést.

```
URL-lista ─▶ szűrés (séma, hoszt, tiltólista) ─▶ robots.txt ─▶ letöltés (safeFetch)
          ─▶ fő tartalom + kód + címsorok ─▶ szakaszok ─▶ releváns szakaszok a kérdéshez
          ─▶ linkjelöltek pontozása ─▶ (keret engedi?) ─▶ következő oldal │ kész
```

## 2. Letöltés szabályai

| Szabály | Érték | Honnan |
|---|---|---|
| Csak nyilvános http(s) hoszt, minden átirányítás újraellenőrizve | `safeFetch` / `publicUrl` | `web/api/_guard.ts` (SSRF-védelem) |
| Időkorlát | 7 s / oldal | `fetchPageText` a `search.ts`-ben |
| Tartalomtípus | `text/html`, `text/plain`, XML | uo. |
| Méretkorlát | ma 4000 karakter szöveg → javaslat: ≤ 2 MB nyers HTML, ≤ 40 000 karakter kinyert szöveg (kiinduló érték) | a 4000 karakter kódos dokuhoz kevés |
| Átirányítás | ≤ 5 | új |
| User-Agent | őszinte, azonosítható (ma `Mozilla/5.0 (compatible; AuriBrain/1)`) | robots-szabályok ehhez illeszkednek |
| Süti, bejelentkezés, űrlapküldés | **nincs** | felhasználási feltételek |
| JavaScript-renderelés | alapból nincs; csak ha a doku enélkül üres, és akkor is külön, korlátozott lépésben | erőforrás + biztonság |

## 3. A fő tartalom kinyerése

A mai `htmlToText` eldobja a `script`/`style`/`nav`/`footer`/`aside`/`form` blokkokat, majd **minden**
címkét → a kódblokkok szerkezete, a nyelvjelölés és a címsor-hierarchia elvész. Programozáshoz ez kevés.
Az új kinyerő DOM-alapú (Node: pl. `@mozilla/readability` + egy DOM-implementáció; Python: pl.
`trafilatura` — a licencet a bevezetéskor ellenőrizni):

1. **Rejtett tartalom eldobása:** `hidden`, `aria-hidden="true"`, `display:none` inline stílus,
   HTML-megjegyzések, nulla szélességű karakterek — ezek a prompt-injekció kedvenc rejtekhelyei.
2. **Fő blokk:** `<main>`, `<article>`, `role="main"`; ha nincs, szövegsűrűség alapján.
3. **Szerkezet megtartása:** `h1–h3` → szakasz-útvonal; `<pre>/<code>` → kódblokk a nyelvvel
   (`class="language-python"`, `highlight-js`, stb.); táblázat → Markdown-táblázat; listák megmaradnak.
4. **Szakaszokra bontás** címsorok mentén, szakaszonként ≤ ~1500 karakter (kiinduló érték).

```ts
interface PageDoc {
  url: string; finalUrl: string; title: string; lang: 'hu'|'en'|'unknown';
  fetchedAt: string; contentHash: string;                 // sha256 a kinyert szövegre → változásfigyelés
  kind: 'docs'|'qa'|'repo'|'blog'|'other';                // a bizalomhoz (03)
  sections: { path: string[]; text: string; code: { lang: string; code: string }[] }[];
  links: { href: string; text: string; sameSite: boolean }[];
  license?: string;                                       // ha az oldal jelzi (pl. CC BY-SA)
  suspicious: boolean;                                     // injekció-gyanú (6. pont)
}
```

A releváns szakaszokat a kérdéshez a meglévő `keySentences` / `rerankSmart` választja ki — a modell
csak ezeket kapja, nem a teljes oldalt (CPU-n a prefill is idő).

## 4. Linkek követése

**Linkpontszám** = a horgonyszöveg és a kérdés kulcsszó-átfedése + azonos webhely (doku) bónusz +
„következő / API reference / Parameters” bónusz − tiltott minták (bejelentkezés, megosztás, hirdetés,
követőparaméterek, fájlletöltés).

| Mód | Mélység | Oldal / kérdés | Hosztonként | Időkeret (kiinduló) |
|---|---|---|---|---|
| interaktív | 1 (csak a találatok) | ≤ 2 | ≥ 2 s szünet | ~15 s |
| tétlen | 2 | ≤ 5 | ≥ 2 s | ~60 s |
| éjszakai tanulás | 2 | ≤ 30 / téma | ≥ 5 s, + `Crawl-delay` | éjszakai összkeret |

A meglátogatott URL-ek normalizálva (`dedup.ts` `normUrl` mintájára) kerülnek egy halmazba; ugyanaz az
oldal egy munkamenetben kétszer nem töltődik le, és a `contentHash` változatlansága esetén éjjel sem.

## 5. Dokumentációs oldalak és ismert típusok

| Típus | Felismerés | Kezelés |
|---|---|---|
| Doku-generátorok (Sphinx, MkDocs, Docusaurus, rustdoc, Javadoc) | meta `generator`, jellegzetes osztálynevek | navigáció a „következő/előző” és az API-index mentén; a `sitemap.xml` csak listának |
| Verziózott doku (`/3.12/`, `/v2/`) | URL-minta | a projekt verziójához illő ág; ha nincs, a `stable`/`latest` |
| GitHub-repó | `github.com/<o>/<r>` | README és `CHANGELOG` nyersen (`raw.githubusercontent.com`); a repót nem járjuk be |
| Stack Overflow / Stack Exchange | URL | csak a kérdés + az elfogadott vagy legmagasabb pontszámú válasz; a pontszám a bizalomhoz megy |
| Blog / cikk | egyéb | csak a fő blokk; alacsonyabb kezdő bizalom |

## 6. robots.txt és felhasználási feltételek

- A `robots.txt` hosztonként letöltve, **24 órára** cache-elve; a saját User-Agentünkre és a `*`-ra
  vonatkozó `Disallow` és `Crawl-delay` kötelező. Ha a `robots.txt` nem érhető el (5xx), az adott hosztot
  aznapra kihagyjuk (konzervatív).
- Oldalszintű jelek: `noindex` / `noai` jellegű `meta robots` esetén az oldalt nem tároljuk tudásként
  (legfeljebb a hivatkozását).
- Fizetőfal, bejelentkezés, CAPTCHA: **nem kerüljük meg**, az oldalt kihagyjuk.
- Tömeges letöltés, teljes oldalak tárolása: nincs — csak rövid kivonat + hivatkozás
  ([04-tanulas-a-webbol.md](04-tanulas-a-webbol.md), licencek).

## 7. A lap tartalma adat, nem utasítás

- A modell minden webes szöveget `<web_adat forras="…">…</web_adat>` blokkban kap, a szerepkönyv
  kimondja, hogy ebben az utasítások figyelmen kívül hagyandók ([../02-belso-parbeszed/04-prompt-sablonok.md](../02-belso-parbeszed/04-prompt-sablonok.md)).
- **Injekció-gyanú jelzése:** mintalista (pl. „ignore (all) previous instructions”, „you are now”,
  „system prompt”, „hagyd figyelmen kívül az utasításokat”, rejtett szöveg) → `suspicious: true`,
  alacsonyabb bizalom, és az oldal szövege **soha** nem kerül eszközhívásra képes kontextusba.
- **Weboldal nem indíthat műveletet:** nincs „a doku szerint futtasd ezt” — a weben talált kód csak
  sandboxban, csak ellenőrzés céljából fut ([../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md)).
- Az oldalakon talált személyes adatot (e-mail, telefonszám) a kinyerő kitakarja, mielőtt bármi tárolódna.

## 8. Kész, ha

1. 10 ismert doku-oldalon (MDN, docs.python.org, nodejs.org, react.dev, …) a kinyerő a kódblokkokat a
   nyelvjelöléssel együtt hiánytalanul visszaadja (kézzel ellenőrzött referencia).
2. A linkkövetés soha nem lépi túl a mód keretét, és egy `Disallow`-olt útvonalat nem tölt le (teszt
   helyi próbaszerverrel).
3. Egy rejtett injekciót tartalmazó próbaoldal `suspicious: true` jelölést kap, és a rejtett szöveg
   nem kerül a szakaszokba.

## Kapcsolódó

- [01-kereses.md](01-kereses.md) · [03-forrasok-es-bizalom.md](03-forrasok-es-bizalom.md) · [04-tanulas-a-webbol.md](04-tanulas-a-webbol.md)
- [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md)
- [../05-tanulas/01-tanulasi-forrasok.md](../05-tanulas/01-tanulasi-forrasok.md) — mely webhelyek a fő tananyagforrások
- [../06-programozas/02-tananyag.md](../06-programozas/02-tananyag.md)
