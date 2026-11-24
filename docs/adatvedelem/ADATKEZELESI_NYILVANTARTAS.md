# Adatkezelési tevékenységek nyilvántartása — AuriGPT

> GDPR 30. cikk (1) bekezdés. Belső dokumentum: nem kell közzétenni, de a felügyeleti
> hatóság (NAIH) kérésére be kell tudni mutatni. **Minden adatkezelési változáskor frissíteni kell**
> (új adatfajta, új szolgáltató, új cél) — ugyanabban a változtatásban, mint a kódot.
>
> Állapot: a kód 2026-11-21-i állapota alapján. Kapcsolódó: `SECURITY.md` 3., 14., 15. fejezet,
> `web/public/adatvedelem.html`, `docs/adatvedelem/DPIA.md`.

## Az adatkezelő

| | |
| --- | --- |
| Név | **[KITÖLTENDŐ]** |
| Cím | **[KITÖLTENDŐ]** |
| Kapcsolat | alexszabi04@gmail.com |
| Adatvédelmi tisztviselő | nincs kijelölve — nem kötelező (37. cikk: nem nagymértékű, rendszeres megfigyelés; nem nagy léptékű különleges adatkezelés). A döntést a lépték növekedésekor újra kell értékelni. |
| Képviselő (27. cikk) | nem releváns (EU-n belüli adatkezelő) |

## 1. Fiók és bejelentkezés

| Szempont | Tartalom |
| --- | --- |
| Cél | felhasználói fiók létrehozása, hitelesítés |
| Jogalap | 6. cikk (1) b) — szerződés teljesítése |
| Érintettek | regisztrált felhasználók (18 év felett) |
| Adatkategóriák | e-mail cím, jelszó-kivonat (a Supabase kezeli, az adatkezelő nem látja), regisztráció ideje, utolsó bejelentkezés, elfogadott feltételek verziója és időpontja, 18+ nyilatkozat (auth metadata) |
| Címzettek | Supabase Inc. (adatfeldolgozó) |
| Harmadik országba továbbítás | a Supabase-projekt régiójától függ — **[KITÖLTENDŐ: régió]**; ha nem EU: SCC / DPF |
| Törlési határidő | a fiók törléséig (felhasználó által indítható: `delete_my_account()`) |
| Biztonsági intézkedések | SECURITY.md 5–6. fejezet: Supabase Auth, RLS, rövid JWT, e-mail megerősítés |

## 2. Beszélgetések tárolása

| Szempont | Tartalom |
| --- | --- |
| Cél | előzmények megőrzése, a beszélgetés folytatása |
| Jogalap | 6. cikk (1) b) |
| Érintettek | regisztrált felhasználók; a szövegben említett harmadik személyek (a felhasználó jegyzeteként) |
| Adatkategóriák | kérdések és válaszok teljes szövege, beszélgetés címe, összefoglaló, kulcsszavak, időpontok |
| Címzettek | Supabase (tárolás) |
| Törlési határidő | a felhasználó törléséig, legkésőbb a fiók törléséig |
| Biztonsági intézkedések | RLS (`auth.uid() = user_id`), HTTPS, automatikus RLS-teszt (`web/supabase/tests/rls_check.sql`) |

## 3. Személyre szabás („memória”, BRAIN)

| Szempont | Tartalom |
| --- | --- |
| Cél | a válaszok személyre szabása a felhasználó saját adataival |
| Jogalap | 6. cikk (1) b) — a szolgáltatás alapfunkciója; a felhasználó a Memória-nézetben bármikor törölheti |
| Adatkategóriák | profil (név, becenév, nyelv, hangnem, „rólam”, érdeklődés), tények, kulcsszavak, feltöltött dokumentumok részletei és összefoglalója, a helyi tanuló állapota |
| Kizárt adatok | jelszó, kártya-, számlaszám, IBAN, TAJ, adóazonosító, igazolványszám, API-kulcs — technikailag szűrve (`web/src/lib/secrets.ts`) |
| Címzettek | Supabase (tárolás); a kérdéshez illő részletek a válaszgeneráláshoz a 4. pont szerinti modellszolgáltatóhoz |
| Törlési határidő | a felhasználó törléséig, legkésőbb a fiók törléséig |

## 4. Válaszgenerálás (nyelvi modell)

| Szempont | Tartalom |
| --- | --- |
| Cél | a felhasználó kérdésének megválaszolása |
| Jogalap | 6. cikk (1) b) |
| Érintettek | regisztrált felhasználók és vendégek |
| Adatkategóriák | az üzenet, a beszélgetés legutóbbi része, a csatolt memória-részletek |
| Címzettek / adatfeldolgozók | 1) az üzemeltető saját gépe (Ollama, Cloudflare-alagúton át) — elsődleges; 2) Groq, Inc. — tartalék; 3) Google (Gemini API) — csak fizetős projekttel (`GEMINI_PAID=1`) |
| Harmadik országba továbbítás | Groq: USA, SCC (Groq DPA 8.2), nem tanít az adatokon (Services Agreement 4.2); Google: USA is, fizetős feltételekkel |
| Megőrzés | az adatkezelő nem tárolja; Groq: alapból nem tárol, visszaélés-vizsgálatra ≤ 30 nap (ZDR bekapcsolásával 0) |

## 5. Webes keresés

| Szempont | Tartalom |
| --- | --- |
| Cél | naprakész információ a válaszhoz |
| Jogalap | 6. cikk (1) b) |
| Adatkategóriák | a kérdésből képzett, személyes adatoktól megtisztított keresőkifejezés (`web/src/autolearn/redact.ts`); a találatok és oldalkivonatok a felhasználó saját tárolójába |
| Címzettek | DuckDuckGo (USA); a találati oldalak (csak a Vercel-függvény IP-címét látják) |
| Megőrzés | a tanult források a felhasználó böngészőjében, identitásonként elkülönítve; lejárati idővel |

## 6. Biztonság és visszaélés-megelőzés

| Szempont | Tartalom |
| --- | --- |
| Cél | a szolgáltatás védelme túlterhelés és visszaélés ellen |
| Jogalap | 6. cikk (1) f) — jogos érdek (érdekmérlegelés: a DPIA 5. pontja) |
| Adatkategóriák | IP-cím vagy felhasználó-azonosító **kivonata** a kérésszámlálóban; időpont, végpont, HTTP-státusz; szervernapló (modell, tokenszám, időtartam, maszkolt kulcs — tartalom és IP nélkül) |
| Címzettek | Vercel (függvények, naplók) |
| Megőrzés | kérésszámlálók: memóriában, legfeljebb 1 nap; Vercel-naplók: a csomag szerinti, ≤ 30 nap; saját szerver: ≤ 30 nap (`journald MaxRetentionSec=30day`) |

## 7. Vendéghasználat

| Szempont | Tartalom |
| --- | --- |
| Cél | kipróbálás bejelentkezés nélkül |
| Jogalap | 6. cikk (1) b) |
| Adatkategóriák | beszélgetések a böngésző helyi tárolójában (az adatkezelő szerverén nem); memória csak a böngészőlap memóriájában |
| Megőrzés | a felhasználó böngészőjében, amíg ő nem törli; a memória a lap bezárásáig |

## Általános biztonsági intézkedések (32. cikk)

A részletes leírás a `SECURITY.md`-ben: elkülönítés RLS-sel (4., 6.), titkok kezelése (7.),
proxy-őr hitelesítéssel, korlátozással, bemenet-ellenőrzéssel és SSRF-védelemmel (8.),
böngészőoldali identitásonkénti tárolás (10.), CSP és biztonsági fejlécek (11.), AI-kockázatok
kezelése (12.), naplózási szabályok (22.), incidenskezelés 72 órás bejelentéssel (23.),
automatikus tesztek (26.).
