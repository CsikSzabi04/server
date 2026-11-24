# Magyarázás és tanítás — szintek, ellenőrzött példák, teach-back

> **Miről szól:** hogyan magyaráz Auri különböző szinteken (kezdőtől szakértőig), hogyan épül fel egy
> jó programozási magyarázat lefuttatott példával, és hogyan használjuk a **teach-back**-et (Auri
> elmagyarázza, amit tanult) a saját tudása ellenőrzésére. Ez a Tanár szerep munkája.

## 1. Két irány

1. **Auri tanít** — a felhasználónak magyaráz (kérdésre, vagy hibakeresés közben).
2. **Auri tanítva tanul** — miután valamit megtanult (web, feladat, éjszakai tanulás), elmagyarázza,
   és a magyarázatát gép ellenőrzi. Ami nem áll össze, az **hiány** → kíváncsiság-kérdés.

Őszintén: a modell súlyai nem tanulnak. A teach-back azt méri, hogy a **tudástár + visszakeresés**
elég-e egy helyes, összefüggő magyarázathoz — vagyis a tudástárat teszteli, nem a modellt.

## 2. Szintek

| Szint | Kinek | Stílus | Példa | Mélység |
|---|---|---|---|---|
| **1 — Kezdő** | most ismerkedik | hétköznapi hasonlat, zsargon nélkül | 3–5 soros, kommentezett | mi ez, mire jó |
| **2 — Haladó kezdő** | ismeri az alapokat | szakszó + rövid magyarázat | teljes, futtatható | hogyan használd |
| **3 — Gyakorló** | dolgozik vele | tömör, idiomatikus | valós helyzet + buktató | mikor *ne* használd, alternatívák |
| **4 — Szakértő** | a belsejére kíváncsi | pontos, hivatkozásokkal | határesetek, teljesítmény | belső működés, specifikáció, verziókülönbségek |

**Szintválasztás**, ebben a sorrendben: (1) kifejezett kérés („magyarázd el egyszerűen” → 1,
„részletesen, belülről” → 4); (2) a kérdés szókincse (sok pontos szakszó → 3–4); (3) a bejelentkezett
felhasználó saját beállítása (a **fiókjában**, nem az agyban); (4) alapérték programozási kérdésnél
**3**, mert a felhasználó fejlesztő (a programozó-orientált persona elve), egyébként 2.

## 3. Egy jó programozási magyarázat szerkezete

1. **Lényeg egy mondatban.**
2. **Minimális, futtatható példa** — a sandboxban **lefuttatva**, a valódi kimenettel. Ha nem futott,
   ki van írva: „(nem futtattam)”.
3. **Lépésenként:** mi történik a példában, soronként vagy blokkonként.
4. **Tipikus hiba + javítás** (lehetőleg egy `fix`-kártyából).
5. **Mikor ne használd / mi a jobb alternatíva** (3–4. szinten).
6. **Forrás:** a hivatalos doku linkje.
7. *(Opcionális)* **Mini-feladat** egy próbateszttel, ha a felhasználó tanulni szeretne.

**Ugyanaz két szinten** — „Mi a különbség a `map` és a `forEach` között?”

*1. szint:* „Mindkettő végigmegy a lista minden elemén. A `map` közben **új listát készít** az
eredményekből, a `forEach` csak csinál valamit minden elemmel, és nem ad vissza semmit.”
```js
const szamok = [1, 2, 3];
const duplak = szamok.map((n) => n * 2);   // [2, 4, 6] — új lista
szamok.forEach((n) => console.log(n));     // kiírja: 1, 2, 3 — nincs visszatérési érték
```

*3. szint:* „A `map` tiszta átalakításra való (új tömb, azonos hossz); a `forEach` mellékhatásra,
`undefined`-dal tér vissza, ezért nem láncolható. Buktató: `async` callbackkel egyik sem várja meg
az ígéreteket — ott `await Promise.all(arr.map(async …))` vagy `for…of` kell. A `forEach`-ből nem
lehet `break`-kel kilépni; ha korai kilépés kell, `for…of` vagy `some`/`find`.”

Mindkét változat példája ugyanabból az ellenőrzött `snippet`-kártyából jön; a szint csak a
magyarázat mélységét és a kiválasztott kártyák körét változtatja.

## 4. Teach-back: tanulás-ellenőrzés magyarázással

```
megtanult téma ─▶ TANÁR: magyarázat 1. és 3. szinten (CSAK a tudástárból, web nélkül)
               ─▶ KÉRDEZŐ: 3 próbakérdés (egy "miért", egy határeset, egy "mi történik, ha …")
               ─▶ TANÁR: válaszok
               ─▶ ELLENŐRZÉS (gép):
                    • minden állítás alátámasztott-e egy ellenőrzött kártyával?
                    • a példák lefutnak-e a sandboxban, és a kimenet egyezik-e?
                    • ellentmond-e valami egy kártyának?
               ─▶ pontszám ─▶ ismétlési ütemezés (05-tanulas) · hiányok ─▶ kíváncsiság-sor
```

```ts
interface TeachBackResult {
  topic: string;
  claims: { text: string; supportedBy: string | null; contradicts: string | null }[];
  examples: { ref: string; ran: boolean; outputMatches: boolean }[];
  probes: { q: string; answeredWithSupport: boolean }[];
  score: number;              // alátámasztott állítások aránya × futó példák aránya (kiinduló képlet)
  gaps: string[];             // → CuriosityItem (02-belso-parbeszed/03-onkerdezes.md)
}
```

Az alátámasztás ellenőrzése: az állítás és a kártya kulcs-/szöveg-hasonlósága (`textSimilar`, később
vektoros hasonlóság), határesetben a Kritikus dönt bizonyítékkal. Költség: egy teach-back kb. 4–6
modell-lépés (becslés: 1–3 perc gemma4:e2b-n) → **csak éjjel vagy tétlenségben** fut (P4).

**Mit jelent az eredmény?** Magas pontszám: a téma kártyái elegendők és összhangban vannak. Alacsony:
hiányzó kártya (→ tanulás), ellentmondó kártyák (→ `vitatott`, újraellenőrzés), vagy a Tanár sablonja
rossz (→ prompt-javítás; ez a mérési naplóban látszik).

## 5. A felhasználó tanítása

- **„Csak tippet kérek” mód:** teljes megoldás helyett szókratészi segítség — egy kérdés, ami a hiba
  felé terel („Mit ad vissza a `forEach`?”), utána egy tipp, csak kérésre a megoldás.
- **Gyakorlás:** a mini-feladat próbatesztjét a felhasználó kódján is a sandbox futtatja; a visszajelzés
  a bukó teszt rövid magyarázata.
- **Adatvédelem:** a felhasználó tudásszintje, haladása **személyes adat** → csak a bejelentkezett
  fiókban tárolható, az agyban soha.

## 6. Prompt (magyar, a persona-munkamenetben)

```text
<kontextus>
<terv>{{tartalomterv_json}}</terv>
Magyarázz {{szint}}. szinten (1 = kezdő … 4 = szakértő). Szerkezet: lényeg egy mondatban →
a tervben lévő, LEFUTTATOTT példa változtatás nélkül → lépésenként → tipikus hiba → forrás.
Csak a terv pontjaiból dolgozz; ami "bizonytalan", azt mondd ki.
</kontextus>
<kérés>{{kerdes}}</kérés>
```

## 7. Kész, ha

1. Minden magyarázatban megjelenő kódpélda vagy lefutott a sandboxban, vagy „(nem futtattam)” jelölést
   visel — automatikus ellenőrzéssel.
2. Ugyanarra a kérdésre az 1. és a 3. szintű válasz mérhetően különbözik (hossz, szakszósűrűség), és
   mindkettő átmegy az [01-ertelmes-mondatok.md](01-ertelmes-mondatok.md) ellenőrzésein.
3. A teach-back 10 próbatémán lefut, és a szándékosan kihagyott kártyák (hiányok) ≥ 80%-át
   `gaps`-ként jelzi (célérték, mérni kell).

## Kapcsolódó

- [01-ertelmes-mondatok.md](01-ertelmes-mondatok.md) · [02-magyar-nyelv.md](02-magyar-nyelv.md)
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) (Tanár) · [../02-belso-parbeszed/03-onkerdezes.md](../02-belso-parbeszed/03-onkerdezes.md) (kíváncsiság-sor)
- [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md) · [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
- [../06-programozas/02-tananyag.md](../06-programozas/02-tananyag.md) · [../06-programozas/08-gyakorlofeladatok.md](../06-programozas/08-gyakorlofeladatok.md)
