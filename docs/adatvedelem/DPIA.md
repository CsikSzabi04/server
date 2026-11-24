# Adatvédelmi hatásvizsgálat (DPIA) — AuriGPT

> GDPR 35. cikk. Belső dokumentum. Elkészítése nyilvános indulás előtt indokolt: a rendszer
> **új technológiát** (generatív MI) használ, **tartós, személyre szabott memóriát** épít a
> felhasználóról, és a promptok egy része **harmadik országba** (USA) jut. Felülvizsgálat:
> évente, valamint minden lényeges változásnál (új modellszolgáltató, új adatfajta, megosztási
> funkció, analitika).
>
> Állapot: 2026-11-21, a kód aktuális állapota alapján. Készítette: **[KITÖLTENDŐ]**.
> Jóváhagyta: **[KITÖLTENDŐ]**. Kapcsolódó: `SECURITY.md`, `docs/adatvedelem/ADATKEZELESI_NYILVANTARTAS.md`.

## 1. Az adatkezelés leírása

Az AuriGPT csevegő asszisztens. A felhasználó kérdésére egy nyelvi modell válaszol; a rendszer a
felhasználó **saját, elkülönített** memóriájából (profil, tények, dokumentumrészletek) a kérdéshez
illő részeket a modellnek küldött utasításhoz csatolja. Bejelentkezve a beszélgetések és a memória a
Supabase-ben tárolódnak, soronkénti hozzáférés-szabályozással (RLS). A válaszgenerálás elsődlegesen
az üzemeltető saját gépén történik (Ollama); ha az nem érhető el, a Groq (USA), és csak fizetős
projekttel a Google Gemini API dolgozza fel a promptot. Opcionális webes keresés esetén a kérdésből
személyes adatoktól megtisztított keresőkifejezés jut a DuckDuckGo-hoz.

Adatfolyam, kategóriák, címzettek, megőrzés: lásd az adatkezelési nyilvántartást és a `SECURITY.md`
2–3. fejezetét.

## 2. Szükségesség és arányosság

| Kérdés | Értékelés |
| --- | --- |
| Szükséges-e a memória a célhoz? | Igen — a szolgáltatás lényege a személyre szabott asszisztens. A felhasználó minden emléket lát, szerkeszthet, törölhet. |
| Kevesebb adattal megoldható? | A belépéshez csak e-mail kell; telefonszám, cím, születési dátum nem. A memória a kérdéshez illő részletekre korlátozódik (≈ 2200 karakter / kérés). Titkok nem kerülnek memóriába. |
| Megőrzés arányos? | A fiók törléséig, a felhasználó által bármikor törölhetően; technikai naplók ≤ 30 nap. Inaktív fiókok automatikus törlése még nincs (SECURITY.md H-7) — a nyilvános indulás után 24 hónapos szabály bevezetése javasolt. |
| Átláthatóság? | Adatkezelési tájékoztató, „MI-vel beszélsz” jelzés minden chat alatt, a válasz forrásának jelölése. |
| Érintetti jogok? | Hozzáférés + adathordozhatóság (teljes JSON-export), helyesbítés, törlés (fiók + kaszkád), panasz (NAIH) — a felületen elérhetők. |
| Automatizált döntés (22. cikk)? | Nincs; a felhasználási feltételek tiltják a nagy kockázatú (AI Act III. melléklet) felhasználást. |

## 3. Kockázatok az érintettekre

Valószínűség (V) és súlyosság (S): alacsony / közepes / magas — **a meglévő intézkedések előtt**.

| # | Kockázat | V | S | Intézkedések | Maradék kockázat |
| --- | --- | --- | --- | --- | --- |
| K1 | Egy felhasználó adatai egy másikhoz jutnak (hibás lekérdezés, séma) | közepes | magas | RLS minden táblán `using` + `with check`; automatikus RLS-teszt negatív kontrollal; kliensszűrés csak kényelmi réteg | **alacsony** |
| K2 | Megosztott böngészőben a következő személy látja az előző fiók adatait | közepes | magas | identitásonkénti helyi kulcsok; kijelentkezéskor takarítás; késleltetett mentés sem írhat vissza; tesztelve | **alacsony** |
| K3 | A prompt (benne memória) harmadik országba jut, a szolgáltató tanít rajta | magas | közepes | elsődleges a saját gép; Groq szerződésben nem tanít, ZDR elérhető; Gemini ingyenes kvóta tiltva; titkok kiszűrve a memóriából; tájékoztatás | **közepes** — csökkenthető: Groq ZDR bekapcsolása, „szigorú privát mód” (csak saját gép) |
| K4 | Titok (jelszó, kártyaszám) tartós memóriába kerül és újra meg újra továbbítódik | közepes | magas | `secrets.ts`: értékalapú felismerés, Luhn-ellenőrzés, kitakarás dokumentumokban; tesztelve | **alacsony** |
| K5 | A modell téves vagy kitalált információt ad, a felhasználó erre döntést alapoz | magas | közepes | persona tiltja a kitalálást; „tévedhet” jelzés; feltételek: nem szakmai tanács; forrásjelölés | **közepes** (a technológia jellege) |
| K6 | Promptbefecskendezés (weboldal, dokumentum) | közepes | közepes | a modellnek nincs eszköze, csak a felhasználó saját adata van a promptban; a kimenet nem fut le; Markdown biztonságosan, HTML nélkül | **alacsony** |
| K7 | XSS → munkamenet-lopás → fiókátvétel | alacsony | magas | React-escape, Markdown React-elemekből, kikényszerített CSP (`script-src 'self'`), `X-Frame-Options` | **alacsony** |
| K8 | Kulcsok kiszivárgása (kvóta- és fiókvisszaélés) | közepes | közepes | kulcsok csak szerveroldalon; `VITE_` szabály; csomagellenőrzés; proxy-őr | **alacsony** |
| K9 | A proxy visszaélésszerű használata (költség, kiesés) | magas | alacsony | eredet-ellenőrzés, hívóazonosítás, kérés- és méretkorlát; `AURI_REQUIRE_LOGIN` | **alacsony–közepes** (példányonkénti számláló) |
| K10 | Kiskorú használja a szolgáltatást | közepes | közepes | 18+ nyilatkozat regisztrációkor, feltételek; tartalmi korlátok | **közepes** (életkor-ellenőrzés nincs) |
| K11 | Különleges adat (egészség, vallás stb.) a memóriában | közepes | magas | nem kérünk ilyet; nem következtetünk rá; a felhasználó látja és törölheti | **közepes** — javasolt: célzott szűrés a tényfelismerőben |
| K12 | Az üzemeltető gépe kompromittálódik (a promptok átmennek rajta) | alacsony | magas | kulcs kötelező, korlátozás, alagút, Ollama csak localhost; üzemeltetési szabályok (SECURITY.md 9.2., 25.4.) | **alacsony–közepes** |

## 4. Döntés

A fennmaradó kockázatok a meglévő és a SECURITY.md 26. fejezetében ütemezett intézkedésekkel
**elfogadható szintűek**; a NAIH-val való előzetes konzultáció (36. cikk) **nem szükséges**, mert
magas maradék kockázat nem maradt. Feltétel: a nyilvános indulás előtt az üzemeltetői teendők
(SECURITY.md 26.) teljesülnek — különösen a jogi oldalak kitöltése, a `delete_account.sql`
telepítése és a Groq ZDR bekapcsolása.

## 5. Érdekmérlegelés (jogos érdek — 6. cikk (1) f), biztonsági naplózás és korlátozás)

1. **Jogos érdek:** a szolgáltatás és a felhasználók védelme túlterhelés, visszaélés és támadás ellen.
2. **Szükségesség:** korlátozás hívóazonosító nélkül nem lehetséges; az IP-cím / felhasználó-azonosító
   csak **kivonatként** szerepel a számlálóban, legfeljebb 1 napig, csak memóriában; a napló tartalmat
   és IP-címet nem rögzít.
3. **Mérlegelés:** az érintettre gyakorolt hatás minimális (nincs profilalkotás, nincs tartós tárolás,
   nincs harmadik félnek átadás), és az érintett észszerűen elvárhatja egy online szolgáltatás
   biztonsági védelmét. **Az adatkezelő jogos érdeke elsőbbséget élvez.**
4. **Tiltakozás:** az érintett tiltakozhat (21. cikk); a kérelmet egyedileg bíráljuk el.
