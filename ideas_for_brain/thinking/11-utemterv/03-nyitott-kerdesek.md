# Nyitott kérdések — amiről a felhasználónak kell döntenie

> **Miről szól:** a terv nyitott döntései (`NK1`…), mindegyiknél opciókkal és **egy javaslattal**. Döntés
> után ide kerül a „Döntés:” sor (dátummal), és a hivatkozó dokumentumok ehhez igazodnak. (Az `NK` előtag
> azért kell, mert a `K1–K6` a biztonsági kapukat, a `T…` a bizalmi és tárolási szinteket jelöli.)

## Összefoglaló

| # | Kérdés | Javaslat | Mikor |
|---|---|---|---|
| NK1 | Hol éljen az Auri Core? | **Döntés (2026-11-21): `auri-core/`, Python, `127.0.0.1:8791`** | P0 előtt |
| NK2 | Milyen sandbox? WSL2 vagy Docker (egyik sincs telepítve)? | **Döntés (2026-11-21): mindkettő mehet** — előbb a BIOS-ban be kell kapcsolni a virtualizációt (SVM); P0: S0 csak saját kódra | P0 / P1 előtt |
| NK3 | Melyik kódoló modell, és mennyi RAM jut neki éjjel? | alapvonal: gemma4:e2b egyedül; a jelölteket már a P0-ban mérjük; 7b, nem 14b | P0 |
| NK4 | Legyen-e felhős tartalék, és tárolható-e a kimenete? | alapból nem; P6-tól feladatonként rákérdezve | P6 előtt |
| NK5 | Bekapcsolva marad-e a gép éjjel, mennyi CPU mehet tanulásra? | **Döntés (2026-11-21): éjjel ki van kapcsolva, napközben sokáig be** → tétlenségi ablakok, újraindítható (checkpointos) feladatok | P4 előtt |
| NK6 | Mely nyelvek először? | TS/JS (Node) + Python → SQL → React → a többi | P0 előtt |
| NK7 | Tanulhat-e a saját (privát) projektjeidből? | csak kijelölt repókból, titokszűréssel, helyben | P4 előtt |
| NK8 | Mennyi várakozás fér bele egy komplex feladatnál? | háttérben, HUD-on követve, 60 perces kerettel | P5 előtt |
| NK9 | Ki bővítheti a csomag-engedélylistát? | Auri javasol, a felhasználó jóváhagy | P5 előtt |
| NK10 | Ki írja az értékelő feladatkészletet? | felhős kódoló ügynök, a felhasználó átnézi | P0 előtt |
| NK11 | Egy közös nyelvfelismerő? | igen, a `brain/lang.ts` szavazós változata a Core-ban | P1 |
| NK12 | Mi legyen a lepárolt, nem ellenőrzött modellválaszokkal? | csak karantén-/hipotézis-státusszal | P1 |
| NK13 | Stack Overflow (CC BY-SA): szerzőnév vagy adatvédelem? | saját, ellenőrzött átírat + URL | P2 előtt |
| NK14 | A hiányzó mérések mikor? | most, a P0 5. lépésében | P0 |
| NK15 | Mi legyen a mai önálló tanuló körrel (`brainChat.ts`)? | maradjon kikapcsolva; a P4 váltja ki | most / P4 |
| NK16 | A licenc nélküli `programming.ingested.ts`? | licenc nélkül nem költözik a Core-ba | P1 |
| NK17 | Írhat-e vendég a közös tudástárba? | **Döntés (2026-11-21): nem — a vendég csak olvas** | P1 |
| NK18 | Angol vagy magyar belső prompt a kódlépésekhez? | A/B mérés a `dev` készleten dönt | P0 |
| NK19 | Kapjon-e a `web/` bekötött tesztfuttatót? | igen, a P5 (L4 a `web/`-en) előtt | P5 előtt |
| NK20 | Melyik modellen fusson a belső szerepkönyv? | qwen3.5:4b, ha a RAM-mérés engedi | P3 előtt |
| NK21 | Hogyan induljon a Core, és elérje-e a hosztolt AuriGPT? | kézzel / igény szerint; eleinte csak helyben | P1 |

## NK1 — Hol éljen az Auri Core?

Opciók: A) a Jarvis-folyamaton belül (a gondolkodás összeomlása a hangot is viszi); **B) külön helyi
Python-szolgáltatás (`auri-core/`, `127.0.0.1:8791`)** — a Jarvis moduljai könyvtárként használhatók, külön
újraindítható; C) Node/TS a `server/` mintájára (a Python-kód és a mérőeszközök újraírandók); D) marad a
böngészőben. **Javaslat: B** — ugyanaz, mint a [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) **javaslata**; a port és a mappa sincs még eldöntve.

## NK2 — Milyen sandbox? WSL2 vagy Docker?

A gépen **nincs** Docker és **nincs** WSL-disztribúció (ellenőrizve, [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)).

| Szint | Mi ez | Mire szabad | Ára |
|---|---|---|---|
| **S0** | Job Object, futási mappa a repón kívül, tiszta env, dedikált futtatókörnyezet kimenő tűzfaltiltással | **csak** Auri saját generálású kódja, saját feladatokon (P0) | egyszeri admin a tűzfalhoz |
| S0+ | S0 külön, alacsony jogú Windows-felhasználóval | ugyanaz, kisebb kockázattal | felhasználó létrehozása (admin) |
| **S1** | WSL2 + saját disztró + `bubblewrap` (nincs hálózat), vagy Docker Desktop | **minden idegen kód** kötelezően: web, `npm`/`pip`, saját repók, L3–L4 | WSL2: admin + újraindítás + GB-ok; Docker: RAM-ja versenyez az Ollamával |
| S2 | Windows Sandbox (Pro-n elérhető) | ritka, kézi kipróbálás | lassú indulás (becslés) |

**Javaslat: P0-ban S0, a P1-ben S1 WSL2 + bubblewrap változattal** (a Docker RAM-igénye miatt). **Kérdés
neked:** telepíthető-e a WSL2 (admin + újraindítás)? Részletek: [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md).

**Döntés (2026-11-21): mindkettő mehet.** Akadály: a CPU virtualizációja a BIOS-ban **ki van kapcsolva**
(`VirtualizationFirmwareEnabled = False`, nincs hypervisor) — enélkül sem a WSL2, sem a Docker, sem a Windows
Sandbox nem indul. Sorrend: 1) BIOS → **SVM Mode: Enabled** (a felhasználó teszi meg); 2) `wsl --install`
(admin + újraindítás); 3) a WSL2 RAM-ja `.wslconfig`-ban korlátozva (pl. `memory=4GB`), hogy az Ollamának
maradjon; 4) Docker **a WSL2-n belül** (Docker Engine; a Docker Desktop is WSL2-re épül, de több RAM-ot visz).
A WSL2 + bubblewrap marad az S1 alapja; a Docker a többfájlos projektekhez (DB-konténer, P5) jön jól.

## NK3 — Kódoló modell és éjszakai RAM

A gemma4:e2b **nem kódoló modell**, kódolási képessége mérve nincs → a P0 első mérése az **alapvonal:
gemma4:e2b egyedül** (`model-only`), utána `+repair`. A kódoló jelölteket **már a P0-ban** ugyanazon a `dev`
készleten mérjük (nem csak a P6-ban); mérőszám: **javítással@3 percenként**.

| Opció | Előny | Hátrány |
|---|---|---|
| A) telepítettek (gemma4:e2b, e4b, qwen3.5:4b) | nincs letöltés; mért sebesség | nem kódolásra hangoltak |
| **B) `qwen2.5-coder:7b`** | kódra hangolt, befér az e2b mellé (~4–5 GB Q4) | lassabb generálás (~3 tok/s) |
| C) `qwen2.5-coder:14b` | jobb minőség várható | ~9 GB: éjjel a Jarvis modelljét ki kell üríteni |
| D) `gpt-oss:20b` / E) 1,5B–3B kódolók | erős / gyors | ~14 GB, mellette semmi / gyenge |

A B–E adatai **becslések**. **RAM-döntés:** a C-hez éjjel kiürül a Jarvis gemma4:e2b-je, és reggel az első
hangkör fizeti a hideg betöltést (mért: 18,5 s). **Javaslat: B**, a C csak akkor, ha a mérés szerint sokkal jobb.

## NK4 — Felhős tartalék (Groq / Gemini)

Opciók: **A) soha (alap)**; B) feladatonként rákérdez; C) automatikusan, csak nyilvános tananyagra; D) mindenre.
**Javaslat: A, a P6-tól B.** Személyes adat és titok egyiknél sem mehet ki. Nyitott: a feltételek engedik-e a
felhős kimenet **tartós tárolását és újrahasznosítását** a tudástárban. A Gemini ingyenes csomagja az EGT-ben
élő felhasználónak nem használható — a `web/api/chat.ts` ezért csak `GEMINI_PAID=1` mellett hívja.

## NK5 — Éjszakai gép és CPU-keret

**Marad-e bekapcsolva a gép éjjel?** Ha nem, tétlenségi ablakok jönnek napközben. Opciók: A) semennyi;
**B) 2 óra/éj fix ablakban, csak tétlenségben**; C) egész éjjel; D) bármikor ≥ 15 perc tétlenség után.
**Javaslat: B**, egy hét után bővíthető. A heti `heldout` mérés (~60 feladat/nyelv × 3–8 perc, becslés)
nyelvenként **3–8 óra** → több éjszakára bontva fut.

**Döntés (2026-11-21): éjjel a gép ki van kapcsolva, napközben viszont sokáig be.** Így a **D** opció érvényes:
nehéz munka bármikor, de csak ≥ 15 perc tétlenség után, és azonnal átadja az Ollama-sávot, ha a felhasználó
visszatér. Minden hosszú feladat (önálló tanulás, `heldout` mérés) **checkpointos**: feladatonként menti az
állapotát, és a következő tétlenségi ablakban (akár újraindítás után) ott folytatja. A `heldout` mérés több
napra bontva fut; egy mérés csak akkor hivatalos, ha mind ugyanazzal a modell- és kódverzióval futott.

## NK6 — Nyelvek

**Javaslat** ([../06-programozas/01-cel-es-szintek.md](../06-programozas/01-cel-es-szintek.md) 5. pont): P0: **TS/JS (Node v24.14.0) + Python 3.12.6**; utána
SQL (SQLite); React csak DOM-emulációval; PostgreSQL/MySQL/Oracle csak S1-es konténerrel; Java/Kotlin/PHP
addig csak L0-tudáskártya. A P0-mini (1 este) lehet csak Python (a `unittest` függőség nélkül fut).

## NK7–NK10 — rövid döntések

- **NK7 saját projektek:** A) nem; **B) csak kijelölt repókból, titokszűrés után, helyben**; C) mind (`.env`,
  kulcs szivároghat). **Javaslat: B**, repónként ([../06-programozas/07-sajat-projektekbol-tanulas.md](../06-programozas/07-sajat-projektekbol-tanulas.md)).
- **NK8 várakozás:** a teljes példa ~47 perc (becslés). A) **háttérben, HUD-on követve, 60 perces kerettel**;
  B) max 10 perc, utána felhő; C) csak részfeladat. **Javaslat: A** (B csak bekapcsolt NK4 mellett).
- **NK9 engedélylista:** A) csak te; **B) Auri javasol (indok, licenc, letöltésszám), te jóváhagyod**;
  C) automatikus küszöb (typosquatting-veszély). **Javaslat: B.**
- **NK10 értékelő készlet:** A) te; **B) felhős kódoló ügynök, te átnézed**; C) Auri (a mért modell ne írja a
  saját vizsgáját). **Javaslat: B** — az `aurikod-hu` (`dev` / `heldout` / `regression` / `public-sanity`), az E2.

## Kódból adódó kérdések (NK11, NK12, NK15–NK17, NK19)

| # | Tény a kódban | Opciók | Javaslat |
|---|---|---|---|
| NK11 | `web/src/autolearn/lang.ts` csak ékezetet néz („ki vagy?” → `en`), `web/src/brain/lang.ts` funkciószavakkal is szavaz (→ `hu`) | marad kettő · **egy közös a Core-ban, közös tesztkészlettel** · LLM · külső könyvtár | közös, a `brain/lang.ts` algoritmusával |
| NK12 | `web/src/brain/distill.ts` `distillFromModel` ellenőrizetlen modellválaszt tárol Q→A párként | marad · **csak karantén-státusszal** · nem tároljuk | karantén; csak modellbizonyítékkal nem lehet `verified`. Név (egyeztetve 2026-11-21): kódban mindig `hypothesis`, magyarul „karantén” — a teljes státuszlista a [tárolási fájlban](../01-architektura/04-tarolas-es-adatfolyam.md) |
| NK15 | `web/src/brain-bridge/brainChat.ts` (alapból kikapcsolt): 90 s-onként fut aktivitástól függetlenül, Ollama nélkül Groq/Gemini-keretet fogyaszt, ellenőrizetlenül párol | marad · gyors javítás · **kikapcsolva marad, a P1-ben lekerül, a P4 váltja ki** | az utóbbi |
| NK16 | `web/src/brain/seed/programming.ingested.ts`: nyers dokumentációs oldalak licencmező nélkül | költözik · **csak egyértelmű forrással és licenccel költözik, a többit a P2 újragyűjti** · eldobjuk | a középső |
| NK17 | ma a böngészős agy a **vendég**-csevegésből is tanul (IndexedDB) | marad · csak karanténba · **vendég csak olvas, semmit nem ír** | az utóbbi (a te döntésed) |
| NK19 | a `web/package.json`-ban csak `tsc --noEmit`; a `web/tests/*.test.ts` kézzel fut (`npx --yes tsx --test`) | marad · **`test` szkript `node:test` + `tsx`-szel** · Vitest | a középső, a P5 előtt (függőség: jóváhagyással) |

## NK13 — Stack Overflow: CC BY-SA vs. adatvédelem

A CC BY-SA forrásmegjelölést kér (szerző, link, licenc), de a felhasználónév személyes adat lehet; ma csak az
URL-t tároljuk. Opciók: A) csak URL; B) szerző + licenc külön licenc-metaadatként (nem kereshető, csak
megjelenítéskor); **C) saját, sandboxban ellenőrzött átírat + az URL „forrásként”**. **Javaslat: C alapból, B
csak elkerülhetetlen szó szerinti részletnél** (nem jogi tanács).

## NK14 — A hiányzó mérések (mind a P0 5. lépésében)

(a) **CPU-s prefill** tok/s (a teljes példa ~40-et feltételez); (b) **KV-cache újrahasználat** azonos prompt
újraküldésekor (az önkonzisztencia-szavazás ára); (c) a gemma4:e2b **érvényes-JSON aránya** `format`-tal
(cél ≥ 95%); (d) kérésenkénti `num_thread` **újratölti-e a modellt**; (e) **megszakítás után** mikor szabad a
sáv; (f) az `OLLAMA_NUM_PARALLEL=1` **modellenként** érvényes — két betöltött modell futhat-e egyszerre, és
mennyire lassítják egymást; (g) az embeddinggemma vektormérete (768?); (h) a qwen3.5:4b RAM-igénye.
**Átmeneti szabály (f)-ig:** amíg a Jarvis hallgat, gondolkodik vagy beszél (`VOICE`), a Core **semmit nem
indít** — a mért versengés (közös sávon az 1. token medián 3,9 s, p90 14,0 s) miatt.

## NK18 — A belső promptok nyelve

Opciók: A) angol belső prompt a kódlépésekhez, magyar magyarázat; B) mindenhol magyar; **C) A/B mérés a
`dev` készleten, modellenként** ([../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md)). **Javaslat: C**; a mérésig A.

## NK20 — Melyik modellen fusson a belső szerepkönyv?

Ha a szerepek (Gondolkodó, Kritikus…) és a Jarvis-persona is a gemma4:e2b-n fut, minden váltás újratölti a
prefixet (mért ~6 s), és **a Jarvis meleg prefixét is törli**. Opciók: A) gemma4:e2b; **B) qwen3.5:4b külön**
(RAM-igénye nincs mérve); C) a kódoló modell. **Javaslat: B**, ha az NK14 (h) mérése szerint belefér.

## NK21 — Indítás és elérés

A Jarvis automatikus indítására azt mondtad: „nem kell”. Opciók az indításra: A) Windows-indításkor; **B) kézzel
vagy igény szerint** (a Jarvis / a helyi AuriGPT indítja első használatkor); C) tálcáról. A hosztolt AuriGPT
csak a `server/`-ben egy **proxy-útvonallal** érné el a Core-t. **Javaslat: B, és eleinte csak helyi
elérés**; a proxy később, tokennel, csak nem személyes végpontokra.

## Kapcsolódó

- [01-fazisok.md](01-fazisok.md) · [02-kovetkezo-lepesek.md](02-kovetkezo-lepesek.md) · [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) · [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md)
- [../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md) · [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md) · [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) (NK20) · [../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md](../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md) (NK11) · [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) (NK13, NK16)
