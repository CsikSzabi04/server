# Ötlettár — ami még nem került tervbe

> **Miről szól:** kreatív, de a gépre és a szabályokra szabott ötletek, amik még nincsenek a P0–P6
> ütemtervben. Mindegyiknél: mit ad, mibe kerül, mi a kockázata, és legkorábban melyik fázis után
> jöhet. Egy ötlet akkor kerül tervbe, ha a fő célt (programozás, komplex feladatok) szolgálja és mérhető.

## 1. Hogyan kerül egy ötlet tervbe

1. Egy oldalas mini-spec: mit csinál, milyen meglévő részre épül, **mi a mérőszáma**.
2. Szabály-ellenőrzés: személyes adat nem kerül az agyba, a web adat és nem utasítás, kód csak
   sandboxban fut, nehéz futás csak tétlenségben.
3. Beillesztés egy fázisba ([../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md)) „Kész, ha” feltétellel.
   Ha a mérés nem mutat javulást, az ötlet visszakerül ide, „kipróbálva, nem segített” megjegyzéssel.

## 2. Áttekintés

| # | Ötlet | Érték | Költség | Kockázat | Legkorábban |
|---|---|---|---|---|---|
| 1 | Modell-párbaj (páros programozás) | magas | közepes (2× CPU) | visszhang | P3 |
| 2 | Kíváncsiság-vezérelt felfedezés | magas | alacsony | rossz témát hajszol | P4 |
| 3 | Tanulás a használt könyvtárak GitHub-issue-iból | magas | közepes | zaj, licenc, injekció | P2 + P4 |
| 4 | Heti „mit tanultam” hangösszefoglaló a Jarvison | közepes (motiváció) | alacsony | unalmas lesz | P1 |
| 5 | Kód-review mód a saját commitjaidra | magas | közepes | sok téves riasztás | P3 |
| 6 | Látható „gondolkodás” panel a HUD-ban és a 3D agyban | közepes | közepes (UI) | teljesítmény | P1 |
| 7 | Mutációs tesztelés: a tesztek tesztelése | magas | alacsony (LLM nélkül) | lassú tesztcsomagnál drága | P0 után |
| 8 | Önjátszó feladatgyártás | közepes | közepes | hibás feladatok | P4 |
| 9 | Hibaüzenet-gyorssegély | magas | alacsony | rossz párosítás | P1 |
| 10 | Könyvtár-verzióőr (elavuló receptek) | közepes | alacsony | hamis riasztás | P2 |
| 11 | Feynman-mód: magyarázva tanul | közepes | közepes | kis modell rossz bírónak | P3 |
| 12 | Gumikacsa-mód neked | közepes | alacsony | idegesítő lehet | P1 |
| 13 | „Reggelre kész” előkészítés | közepes | közepes | adatvédelem, elpazarolt CPU | P4 |
| 14 | Gondolkodási költségmérő | alacsony–közepes | alacsony | pontatlan becslés | P1 |

## 3. Az ötletek röviden

**1. Modell-párbaj.** Két szerep (vagy két modell) versenyez ugyanazon a feladaton: az egyik a teszteket
írja, a másik a kódot; vagy két független megoldás készül, és a tesztek döntenek. A vesztes hibája
hibamintaként tárolódik. *Mérőszám:* javítással@3 **percenként** — egy sávon a két megoldás sorban fut, tehát
csak akkor éri meg, ha a siker többet nő, mint az idő. *Kockázat:* két kis modell ugyanazt a hibát véti.

**2. Kíváncsiság-vezérelt felfedezés.** Az éjszakai tanulás témáját egy pontszám választja:
`kíváncsiság = bukási arány a témában × mennyire használod (a projektjeid importjai) × újdonság`.
Egy téma akkor „megtanult”, ha az ismétléskor 3-szor egymás után zöld. *Kockázat:* olyan témát hajszol,
amit a modell sosem tud megoldani → témánként kerete van, utána „parkolt”.

**3. Tanulás a GitHub-issue-kból.** A kijelölt projektjeid `package.json` / `requirements.txt` függőségeihez
lezárt „bug” issue-k + a javító commit → **hibaminta-jelöltek**; ellenőrzött tudás csak akkor lesz belőle,
ha a hibát a sandboxban reprodukálni és a javítással zöldre fordítani is sikerül. Az issue-szöveg adat,
nem utasítás. *Költség:* API-keretek (nem garantált ingyenes limitek), lassú ellenőrzés.

**4. Heti „mit tanultam” a Jarvison.** Vasárnap este (vagy „Hey Auri, mit tanultál a héten?”) 5 mondat a
fejlődési naplóból: hány feladat, mi lett jobb, min akadt el. A **Piper** helyi hangjával (első hang mért
medián 170 ms), nem ElevenLabs-szel — a havi 2000 kredites keret marad a rögzített mondatoknak.

**5. Kód-review mód.** Kijelölt repóidon tétlenségben a friss commitok diffjét a Kritikus átnézi. Előbb
titokszűrés; „biztos” jelölést csak linter- vagy bukó teszttel igazolt észrevétel kap, a többi
„kérdés”. Soha nem commitol és nem pushol. *Mérőszám:* hány észrevételt fogadsz el (pontosság).

**6. Gondolkodás-panel.** A Core `think.*` eseményei (`plan`, `task`, `check`, `learned`) idővonalként a
Jarvis HUD-on; a `/brain` 3D nézetben a feladat témájához tartozó régió felvillan, és új csomópont
„születik”, amikor ellenőrzött tudás kerül a tárba. Személyes adat itt sem jelenhet meg.

**7. Mutációs tesztelés.** Egy zöld megoldásba apró hibákat ültetünk (operátorcsere, ±1, feltétel
tagadása) — a teszteknek el kell bukniuk. Ha egy mutáns „túléli”, a tesztek gyengék → a Tesztelő új
tesztet ír. LLM nem kell hozzá, csak sandbox-futtatás → **olcsó**, és a tárolt tudás minőségét javítja.

**8. Önjátszó feladatgyártás.** Auri a tananyagból feladatváltozatokat generál; érvényes csak akkor,
ha a referencia-megoldása zöld és a tesztjei átmennek a mutációs próbán (7.). „Generált”, alacsonyabb
bizalommal jelölve, és **soha** nem kerül az értékelő készletbe (a mért modell ne írja a saját vizsgáját).

**9. Hibaüzenet-gyorssegély.** Bemásolsz egy hibaüzenetet (AuriGPT) vagy felolvasod (Jarvis) → az
aláírását a hibaminták között keresi → pontos találatnál **0 LLM-hívással**, forrással válaszol; ha
nincs találat, a normál út (web, modell). A P0 hibakivonat-normalizálója újrahasznosul.

**10. Könyvtár-verzióőr.** A receptekben használt könyvtárak kiadási jegyzeteit figyeli (pl. Express 5,
React új főverzió) → az érintett receptek „elavulhat” jelölést kapnak, és újraellenőrzésre kerülnek az
éjszakai sorba. *Kockázat:* zajos kiadási jegyzetek → csak főverzióra riaszt.

**11. Feynman-mód.** A Tanár magyar magyarázatot ír egy fogalomról; egy kisebb „diák” modell (pl.
gemma4:e2b, tudástár nélkül) **csak abból** válaszol egy kvízre. Ha elbukik, a magyarázat homályos →
átírás. A jó magyarázatok neked is olvashatók. *Kockázat:* a kvízt is kis modell pontozza → zárt kérdések.

**12. Gumikacsa-mód.** Kérésre („segíts gondolkodni, ne mondd meg”) Auri a válasz helyett kérdez:
„Mit vársz ezen a soron? Mit kapsz?” A Tanár szerep fordítottja; alacsony költség, a Jarvis hangján is működik.

**13. „Reggelre kész”.** Ha engedélyezed, a napi munkád témái (a kijelölt repók git-aktivitásából, nem a
tartalmából) alapján éjjel előkészít: releváns recepteket, dokumentáció-kivonatokat, vázat. *Kockázat:*
adatvédelem (csak témák, helyben) és elpazarolt CPU, ha nem használod → mérni, mennyit nyitsz meg belőle.

**14. Gondolkodási költségmérő.** Feladatonként CPU-perc, token, és egy durva energiabecslés (a CPU
névleges TDP-je × idő — **becslés**, nem mérés). Láthatóvá teszi, mibe kerül egy „gondolkodás”, és
segít a keretek beállításában ([../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md) NK5, NK8).

## 4. Parkoló — most nem reális, de ne vesszen el

- **Saját kis modell finomhangolása (LoRA) az ellenőrzött megoldásokon.** CPU-n nem reális (becslés);
  felhős GPU-val igen, de akkor az adat elhagyja a gépet → csak nyilvános, nem személyes tananyaggal, külön döntéssel.
- **VS Code-bővítmény** a Core-hoz (kijelölés → „Auri, nézd meg”). Hasznos, de nagy UI-munka — P5 után.
- **Több gép összekapcsolása** (pl. egy erősebb gép a hálózaton mint második Ollama-sáv) — ha lesz ilyen gép.

## Kapcsolódó

- [../thinking.md](../thinking.md) · [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) · [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)
- [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) · [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)
- [../06-programozas/08-gyakorlofeladatok.md](../06-programozas/08-gyakorlofeladatok.md) · [../06-programozas/07-sajat-projektekbol-tanulas.md](../06-programozas/07-sajat-projektekbol-tanulas.md)
- [../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md](../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md) · [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)
- [../03-web-szorfozes/04-tanulas-a-webbol.md](../03-web-szorfozes/04-tanulas-a-webbol.md) · [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md)
