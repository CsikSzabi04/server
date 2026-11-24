# Amit nem szabad megtanulni — tiltólista, szűrők, tanulság egy valós esetből

> **Miről szól:** mi az, ami **soha** nem kerülhet a tudástárba (személyes adat, titok, licencelt
> tömeges tartalom, ellenőrizetlen ártalmas utasítás, prompt-injekció, kiértékelő megoldások), hogyan
> működik a tiltó kapu (`canLearn`), hol téved, és mit javítottunk a 2026-11-20-i eset után, amikor a
> kijelentkezett BRAIN felmondta a felhasználó profilját.

## 1. A tiltólista

| Kód | Kategória | Példa (fiktív) | Szűrő — ma / terv |
|---|---|---|---|
| T1 | Személyes adat | „A nevem Teszt Elek, 2001. március 5-én születtem.” | `isPersonal()` — `web/src/brain/privacy.ts` (ma) |
| T2 | Titok | „a jelszavam Kutya123”, `GROQ_API_KEY=gsk_…`, kártyaszám | `containsSecret()` — `web/src/lib/secrets.ts` (ma) |
| T3 | Különleges adat (egészség, vallás, politikai nézet…) | „cukorbeteg vagyok” | terv: kategória-szűrő (`SECURITY.md` 3.5, GDPR 9. cikk) |
| T4 | Harmadik személy adata | „a kollégám, Minta Máté címe …” | részben (`isPersonal`); terv: névfelismerés |
| T5 | Licenc miatt nem tárolható tartalom | teljes doksioldal, könyvfejezet, GPL-kód szó szerint | terv: licenc-kapu (2. pont) |
| T6 | Ellenőrizetlen ártalmas utasítás | „gyorsítsd a gépet: `Remove-Item -Recurse C:\…`” | terv: veszélyes-parancs minták |
| T7 | Prompt-injekció | „MI-asszisztens: hagyd figyelmen kívül az eddigieket…” | terv: injekció-detektor ([../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md)) |
| T8 | Kiértékelő feladat és megoldása | held-out feladat szövege, referenciamegoldás | terv: eval-tiltólista hash-ekkel |
| T9 | Gépre/személyre utaló azonosító | `C:\Users\<név>\…`, gépnév, belső IP | terv: útvonal-normalizálás (`<HOME>`) |

Nem tiltás, de rokon szabály: ellenőrizetlen modell-állítás nem lehet **tény** — karanténba megy
([04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)). Veszélyes parancsról **tudni** szabad
(„a `rm -rf` rekurzívan töröl”); tilos olyan receptet tárolni, ami ellenőrzés nélkül ilyet futtatna.

## 2. Licencek — mit tárolhatunk

| A forrás licence | Mit tárolhatunk |
|---|---|
| MIT, BSD, Apache-2.0, ISC, PSF, CC0 | kódot is, a licenc és a forrás megjelölésével |
| CC BY / CC BY-SA (pl. MDN-szöveg, Stack Overflow) | rövid kivonat + saját szavas összefoglaló + link + forrásmegjelölés; szó szerinti átvételnél a feltételek öröklődnek |
| GPL / AGPL | snippettárba szó szerint **nem** (ne szivárogjon a felhasználó projektjébe); leírás + link |
| Ismeretlen, „minden jog fenntartva”, fizetős | csak link és rövid, saját szavas összefoglaló |

Ma a `web/src/brain/seed/programming.ingested.ts` nyers oldalkivonatokat tárol licenc-mező nélkül —
P1-ben át kell nézni és `license` mezővel ellátni (vagy linkre és összefoglalóra cserélni).

## 3. A kapu: `canLearn()`

```ts
type Rule = 'T1' | 'T2' | 'T3' | 'T4' | 'T5' | 'T6' | 'T7' | 'T8' | 'T9';
type Verdict = { ok: true } | { ok: false; rule: Rule };

function canLearn(c: Candidate, ctx: { knownNames: string[] }): Verdict {
  try {
    if (containsSecret(c.text)) return deny('T2');               // a legsúlyosabb előre
    if (isPersonal(c.text, ctx.knownNames)) return deny('T1');
    if (isSpecialCategory(c.text)) return deny('T3');
    if (looksLikeInjection(c.text)) return deny('T7');
    if (isEvalItem(c.text)) return deny('T8');
    if (isDangerousCommand(c.text) && c.kind !== 'fact') return deny('T6');
    if (!licenseAllows(c.provenance, c.kind)) return deny('T5');
    return { ok: true };                                         // → karantén, NEM a tudástár
  } catch {
    return deny('T1');                                           // fail-closed: hibánál nem tanul
  }
}
```

Szabályok a kapuhoz:

- **Egyetlen bejárat:** minden tanulási út ezen megy át (beszélgetés, web, doksi, saját kód,
  modell, önálló tanulás, kudarc). Új út csak a kapuval együtt kerülhet be.
- **Fail-closed:** ha a szűrő hibát dob, a jelölt nem tanulódik meg.
- **A napló nem szivárogtat:** tiltáskor csak `rule`, `source`, időbélyeg és egy hash kerül a
  naplóba — a szöveg soha (különben a napló tárolná a személyes adatot).
- **Visszamenőleges takarítás:** új szabálynál a teljes tudástár újra átmegy a kapun (ahogy ma a
  `useBrainLearning` `scrubPersonal()` a betöltéskor kiszűri a régi személyes Q→A párokat).
- **Kifelé is:** webkeresés előtt `redactForSearch()` (`web/src/autolearn/redact.ts`), felhő felé
  ugyanez + `containsSecret` ([../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md)).

## 4. Hol téved a szűrő (őszintén)

- Regex-alapú, **legjobb szándékú** szűrő, nem garancia. Téves negatív: „Szegeden élek.” — az
  „élek” nincs a mintákban (a „lakom” igen), így ma átmenne. Ilyen esetet tesztbe kell venni és a
  mintát bővíteni.
- Téves pozitív: a `\b\d{6,}\b` minta miatt egy `setTimeout(fn, 100000)` sor „személyesnek” számít,
  és az a kör nem tanulódik meg. Ez elfogadható ár: a `privacy.ts` szándékosan a „személyes” felé hibázik.
- A név csak akkor szűrhető, ha ismert (`knownNames` — a bejelentkezett profilból).
- Később (P4+, becslés) egy kis helyi osztályozó kiegészítheti, de a regex-kapu marad az első vonal.

## 5. Az eset: a kijelentkezett BRAIN felmondta a profilt

**Mi történt (2026-11-20, `BRAIN_BUILD.md` napló és `web/tests/brain-answers.test.ts`):** kijelentkezve
a BRAIN olyan üzenetekre, mint „nem”, „nmem” vagy „mi a …?”, a felhasználó teljes személyes profilját
mondta fel (születési adat, egyetem, munkahely).

**Okok:** (1) a vendégmód régi, közös `localStorage`-kulcsokból (`auri.profile`, `auri.memories`)
olvasott; (2) a `pickFacts` a kitűzött profilt **minden** üzenethez relevánsnak vette; (3) a tanuló
személyes Q→A párokat is megtanulhatott; (4) fiókváltáskor versenyhelyzetben a bejelentkezett agy a
vendég IndexedDB-be is mentődhetett.

**Javítások:**

1. `web/src/lib/memStore.ts`: a vendég profilja és emlékei csak a lap memóriájában élnek; a régi
   kulcsokat soha többé nem olvassuk; bejelentkezve minden a Supabase-ben (RLS: `auth.uid() = user_id`).
2. `privacy.ts` `isPersonal()` kapu a `useBrainLearning` `observe()` és `distill()` útján; betöltéskor
   `scrubPersonal()`; az `answer.ts` recall személyes mondatot nem ad vissza.
3. `answer.ts` `pickFacts`: a kitűzött emlék csak valódi kulcsszó-átfedésnél számít.
4. `useBrainLearning`: identitásváltáskor azonnal friss, seedelt agy; a `persist()` csak a betöltött
   identitás tárolójába ír.
5. Tesztek fiktív adattal („Teszt Elek”): `brain-answers.test.ts`, `privacy-isolation.test.ts`.

**Tanulság a gondolkodó agynak:** az identitás minden tárolási művelet része; a közös tudástár
általános tudás, a személyes tény csak a fiók tárolójában él; minden kiadás előtt fut egy
regressziós teszt, ahol kijelentkezett munkamenet fiktív profillal próbál adatot „kicsalni”.

## Kész, ha

- a `canLearn()` az egyetlen út a karanténba, és teszt bizonyítja, hogy minden forrás átmegy rajta;
- a T1–T9 mindegyikére van legalább 3 fiktív, tiltandó és 3 megengedett példa a tesztkészletben
  ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)), és mind zöld;
- a tiltásnapló semmilyen szöveget nem tartalmaz, csak szabálykódot és hash-t;
- a kijelentkezett munkamenetes regressziós teszt minden kiadás előtt zöld.

## Kapcsolódó

- [01-tanulasi-forrasok.md](01-tanulasi-forrasok.md) · [04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) · [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md)
- [../03-web-szorfozes/04-tanulas-a-webbol.md](../03-web-szorfozes/04-tanulas-a-webbol.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
