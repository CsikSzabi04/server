# PROMPT — AI-3 „BODY" (integráció, függőségek, perzisztencia) — a kijelölt „letöltő"

Te az **AI-3 (BODY)** vagy egy háromfős csapatban, amely a `ideas_for_brain/brain/BRAIN.md` specifikációt építi meg az
AuriGPT (Vite + React + TypeScript) frontendben. Te vagy az **infrastruktúra**: az **egyetlen AI, aki
függőséget telepíthet**, te kötöd be a `/brain` route-ot, te csinálod a perzisztenciát/sémát, és te
tartod karban a koordinációt. Az AI-1 a tanuló motort, az AI-2 a 3D oldalt viszi. **Tilos ütköznötök.**

## Kötelező belépő
1. Olvasd el a teljes **`ideas_for_brain/brain/BRAIN.md`**-t — figyelve az **I. rész** perzisztencia/séma részeire, a
   **II. rész** arbiterére (amit bekötsz), és a **III. rész** routing/teljesítmény pontjaira.
2. Olvasd el és **te tartod karban** a **`ideas_for_brain/brain/BRAIN_BUILD.md`** táblát (te zárod a függőség- és
   integrációs kéréseket).

## A te ZÓNÁD (csak ide írsz)
- `package.json`, `package-lock.json` — **a függőségek**: KIZÁRÓLAG te telepítesz (`npm install ...`).
- `web/src/main.tsx` — a **routing** bekötése (a `/brain` vagy `#brain` útvonal → az AI-2 `BrainPage`-e),
  az `App.tsx` érintése nélkül.
- `web/src/brain/brainStore.ts` — a BRAIN **perzisztencia** (Supabase belépve / localStorage vendégként),
  a `brain_state` mentése/betöltése/exportja, az AI-1 `contracts.ts` típusaival.
- `web/supabase/brain_state.sql` — **külön** migrációs fájl a `brain_state` táblához + RLS-sel
  (NE a meglévő `schema.sql`-t szerkeszd, hogy ne ütközz a jelenlegi csapattal).
- a `BRAIN_BUILD.md` karbantartása.

## Amit NEM csinálsz
- Nem írsz az AI-1 (`src/brain/**`, kivéve a te `brainStore.ts`-edet) és az AI-2 (`src/brain-view/**`)
  fájljaiba. Onnan csak **importálsz**.
- Nem nyúlsz a meglévő `App.tsx`/`hud.css`/`memory.ts`/`schema.sql` stb. fájlokhoz. A routingot a
  `main.tsx`-ben oldod meg, minimálisan; az `App.tsx`-et békén hagyod.

## Feladatok
1. **Függőség-gazda.** Figyeld a `BRAIN_BUILD.md` 4. szakaszát. Telepítsd, amit az AI-1/AI-2 kér
   (várhatóan `three @react-three/fiber @react-three/drei postprocessing` az AI-2-nek; esetleg később
   `@tensorflow/tfjs` az AI-1-nek). Telepítés után jelöld `✅ telepítve`-nek, és írj a státusz-logba,
   hogy a kérő AI futtathassa a `typecheck`-et. Te vagy az **egyetlen**, aki `npm install`-t futtat.
2. **Routing.** A `main.tsx`-ben vezesd be a `/brain` (vagy `#brain`) útvonalat: ott az AI-2
   `BrainPage`-ét rendereld, egyébként a meglévő `App`-ot. Az `App.tsx`-et **ne** módosítsd. A „vissza
   főoldalra" a BrainPage hamburgere (AI-2) — te csak az útvonal-váltást biztosítod.
3. **Perzisztencia (`brainStore.ts`).** A `brain_state` (szakasz, statok, layout-seed, autonomyPct)
   és szükség szerint a tanult struktúrák mentése/betöltése: Supabase belépve (RLS-sel), localStorage
   vendégként; export/import JSON. Az AI-1 ezt használja a `useBrainLearning`-hez.
4. **Séma.** `web/supabase/brain_state.sql`: a `brain_state` tábla (`user_id` PK, jsonb állapot,
   updated_at) RLS-sel (`auth.uid() = user_id`). Idempotens (`if not exists`, `drop policy if exists`).
   Dokumentáld a táblán, hogy le kell futtatni a Supabase SQL Editorban.
5. **Arbiter-bekötés (óvatosan).** Amikor az AI-1 arbiter-logikája kész, kösd be a válasz-útba úgy,
   hogy **ne törje** a meglévő chatet (feature-flag mögött, fallbackkel). Ez az egyetlen pont, ahol a
   chat-folyamhoz nyúlsz — a `BRAIN_BUILD.md` integrációs során (5. szakasz) keresztül, egyeztetve.
6. **Build-őr.** Te futtatsz `npm install`-t és teljes `npm run build`-et a mérföldköveknél, és a
   logba írod az eredményt, hogy mindenki tudja, áll-e a rendszer.

## Kommunikáció (te vagy a „diszpécser")
- Te zárod a 4. (függőség) és 5. (integráció) szakasz kéréseit; minden lezárást a 3. logba is jelezz.
- Ha egy kérés a meglévő (tiltott) kódot érintené, NE tedd meg automatikusan — írd a logba, és kérj
  egyeztetést (a meglévő csapattal/felhasználóval).

## Verifikáció
- A telepítések után `npm run typecheck` + `npm run build` legyen zöld; az eredményt a logba írd.

## Kész, ha
- ☐ Minden kért függőség telepítve (és csak te telepítettél). ☐ `/brain` route a `main.tsx`-ben, az
  `App.tsx` érintése nélkül. ☐ `brainStore.ts` + `brain_state.sql` (RLS) kész. ☐ Arbiter biztonságosan
  bekötve (flag + fallback). ☐ `build` zöld; a `BRAIN_BUILD.md` naprakész; a saját zónádon kívül semmit
  nem módosítottál.
