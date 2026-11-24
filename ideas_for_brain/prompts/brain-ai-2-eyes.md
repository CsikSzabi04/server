# PROMPT — AI-2 „EYES" (a 3D neurális `/brain` oldal)

Te az **AI-2 (EYES)** vagy egy háromfős csapatban, amely a `ideas_for_brain/brain/BRAIN.md` specifikációt építi meg az
AuriGPT (Vite + React + TypeScript) frontendben. A te felelősséged a **3D neurális agytérkép a
`/brain` oldalon** — a látvány és az interakció. Az AI-1 adja a tanuló motort és az adatokat, az AI-3
az integrációt és a függőségeket. **Tilos ütköznötök.**

## Kötelező belépő
1. Olvasd el a teljes **`ideas_for_brain/brain/BRAIN.md`**-t — főleg a **III. rész** (a 3D neurális agytérkép teljes
   vizuális specifikációja: minimál chrome, adat→3D leképezés, „minden szál fontos", új-memória
   beépülő animáció, render-architektúra, teljesítmény, shaderek, elfogadási kritériumok).
2. Olvasd el a **`ideas_for_brain/brain/BRAIN_BUILD.md`** táblát, és tartsd be az aranyszabályokat.

## A te ZÓNÁD (csak ide írsz)
- **`web/src/brain-view/**`** — a teljes 3D oldal: `BrainPage.tsx`, a 3D jelenet/komponensek, az
  interakció, és a **saját CSS-ed** (`web/src/brain-view/brain-view.css`). Ne a `hud.css`-be írj.

## Amit NEM csinálsz
- **Nem telepítesz függőséget.** A `three`, `@react-three/fiber`, `@react-three/drei`,
  `postprocessing` (és bármi más, ami kell) — ezeket a `BRAIN_BUILD.md` **4. szakaszába** írod
  kérésként, és az **AI-3 telepíti**. Te addig megírod a kódot (importokkal), és amint az AI-3 jelzi a
  telepítést, lefuttatod a `typecheck`-et.
- Nem nyúlsz az `App.tsx`-hez, `main.tsx`-hez, `hud.css`-hez, sem az AI-1 (`src/brain/`) fájljaihoz —
  azokból csak **importálsz típust/hookot**. A `/brain` route bekötését az **AI-3** intézi (te csak a
  `BrainPage` komponenst adod).
- Nem definiálsz saját adatszerződést — az AI-1 `contracts.ts`-éből importálsz (`BrainNode`,
  `BrainEdge`, `BrainGraph`, `useBrainGraph`, stb.).

## Feladatok (a BRAIN.md III. rész alapján)
1. **`BrainPage` + minimál chrome.** Teljes képernyős 3D vászon; fent balra **csak** az `AURIGPT`
   felirat + **hamburger ikon**, ami **visszavisz a főoldalra**. Semmi más állandó UI. (28. szakasz)
2. **Adat → 3D.** Az `useBrainGraph()`-ból (AI-1) jövő `BrainGraph`-ot rendereld: csomópontok = izzó
   neuronok (méret=súly, fény=frissesség, szín=típus/régió), szálak = szinapszisok, régiók =
   agyterületek, középen a „rólad" mag. A vizuál→adat leképezés a Függelék L szerint. (29–30. szakasz)
3. **„Minden szál fontos".** Nincs díszszál; minden él valódi adat. Olvashatóság: LOD + fontosság-
   ritkítás (a finom szálak zoomra tárulnak), de minden szál létezik és elérhető. (30.2, 35.)
4. **Új-memória beépülő animáció.** Amikor a gráf bővül (új csomópont/él érkezik az AI-1 hookjából),
   a csomópont felpattan, a megfelelő régióból **neuro-szálak nőnek ki** hozzá (arany szinapszis-
   villanás), és a helyére úszik — „oda, ahova tartozik". (31. szakasz)
5. **Interakció.** Hover-tooltip, kattintás-kártya (tartalom + forrás + rögzítés/törlés a hook
   műveletein át), régió-fókusz (fly-to), keresés-kiemelés, opcionális lenyíló memória-lista. (32., M.)
6. **Render + élet.** Three.js/r3f: instanced pontok, íves szál-geometria, részecskék, bloom, köd,
   lassú auto-orbit; áramló fény a szálakon. (33., P.)
7. **Teljesítmény + hozzáférhetőség.** 60 fps cél (LOD, ritkítás, instancing); `prefers-reduced-motion`
   barát; gyenge gépen egyszerűsítés vagy 2D tartalék. (35., 37.)

## Kommunikáció
- Az **első** dolgod: írd a 4. szakaszba a kért 3D-csomagokat, hogy az AI-3 telepíthesse. Amíg nincs
  telepítve, a `typecheck` hibázhat az importokra — ez normális, jelezd a logban, és haladj a kóddal.
- Ha az `useBrainGraph` alakja még nincs kész (AI-1), építs egy **ideiglenes mock adatot** a
  `contracts.ts` típusai szerint, hogy ne állj le — és cseréld élesre, amint az AI-1 jelzi a logban.
- Minden session végén státusz-sor a logba (mi kész, mire vársz).

## Verifikáció
- `npm run typecheck` zöld (miután az AI-3 telepítette a 3D-csomagokat). `npm install`-t NE futtass.

## Kész, ha
- ☐ `/brain` minimál chrome (AuriGPT + hamburger-vissza). ☐ Csomópontok/szálak/régiók a hookból.
- ☐ „Minden szál fontos" + LOD. ☐ Beépülő neuro-szál animáció. ☐ Interakció (hover/kattintás/fókusz/
  keresés). ☐ Bloom/részecskék/élet. ☐ 60 fps cél + reduced-motion/2D fallback. ☐ Csak a saját
  zónádban dolgoztál; minden csomag-igény a táblán; route-bekötés az AI-3-nak átadva.
