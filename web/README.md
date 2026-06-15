# AuriGPT — élő HUD chat frontend

Teljes képernyős, animált **J.A.R.V.I.S. stílusú** AI-chat felület (Vite + React + TS).
Alapból **MOCK módban** fut (backend nélkül is teljes az élmény), és egyetlen env-változóval
ráköthető a privát [Auri-szerverre](../server/README.md) — **biztonságosan, a kulcs kiszivárgása nélkül**.

## Vizuális extrák

- **3D arany energiagömb (MindCore):** a központi mag valódi WebGL-jelenet (Three.js +
  react-three-fiber + bloom) — részecskehéj, forró mag, energiavonalak/szinapszis-szikrák,
  gyűrűk, glow-haló, kamera-lélegzés. Reagál az `auriState`-re
  (idle/listening/thinking/speaking/error) interpolált átmenetekkel; thinkingnél felpörög,
  errornál vörösre vált. **Fallback:** ha nincs WebGL vagy `prefers-reduced-motion` aktív →
  a 2D cián reaktor. A nehéz 3D bundle lazy-betöltött, és ErrorBoundary védi.
- **Pixel-lakók (Residents):** két **eredeti, paródia-jellegű** pixel-art figura —
  „DOC-R" (örült-tudós archetípus) és „THE TRAVELLER" (rejtélyes utazó archetípus).
  ⚠️ **Nem** hivatalos/védjegyzett karakterek másolatai: saját rajzolt, parametrikus
  sprite-ok, eredeti nevekkel/színekkel és saját magyar paródia-egysorosokkal. Random
  sétálnak, 10+ akciót játszanak (idle/walk/wave/jump/think/laugh/trip/point/gadget/sit/dance/
  glitch), néha beszélgetnek/kergetőznek, és reagálnak Auri állapotára. A fejlécben
  kapcsolhatók (👾 LAKÓK), `prefers-reduced-motion`-barát, `pointer-events:none`
  (nem zavarják a chatet).

## Fejlesztés

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc --noEmit + vite build  -> dist/
npm run preview    # a buildelt változat kiszolgálása
```

### Lokális ÉLES mód (valódi Ollama-válaszok a 5173-on)

A `web/.env.local`-ban (gitignore-olt) legyen `VITE_API_URL=/api/chat`. Ekkor a `vite.config.ts`
beépített dev-proxy middleware-e a böngésző `/api/chat` hívását továbbítja a backend `:8787/v1/chat`-jére,
és **szerveroldalon hozzáadja a kulcsot** (amit automatikusan a `../server/.env`-ből olvas — a kulcs
sosem kerül a böngészőbe). Előfeltétel: fusson a backend (`cd ../server && npm start`) és az Ollama.
Indításkor a Vite kiírja: `[auri proxy] /api/chat -> … | key: loaded ✓`.
`VITE_API_URL` nélkül a felület MOCK módban marad.

## Üzemmódok (`VITE_API_URL`)

| `VITE_API_URL` | Mód | Mikor |
|----------------|-----|-------|
| *(üres)* | **MOCK** | demó / GitHub Pages — backend nélkül is animált, válaszol |
| `/api/chat` | **PROXY** | **éles, Vercelen** — a kulcs a serverless proxyban van (titok) |
| `https://…/v1/chat` | **DIRECT** | csak privát/lokális teszt — ⚠️ a kulcs a kliensbe kerülne |

> ⚠️ **Biztonság:** minden `VITE_*` változó **beégetődik a publikus kliens-bundle-be**.
> Éles, publikus deployon **soha** ne tedd a valódi kulcsot `VITE_API_KEY`-be — használd a
> PROXY módot, ahol a kulcs csak a Vercel serverless függvényben él.

## Deploy Vercelre (ajánlott — ez ad biztonságos proxyt)

1. Pushold a repót GitHubra (a gyökér `.gitignore` kizárja a titkokat és a nagy binárisokat).
2. Vercel → **Add New Project** → importáld a repót.
3. **Root Directory = `web`** (fontos: a monorepo miatt).
   Framework: Vite (auto). Build: `vite build`, Output: `dist` (a `vercel.json` is rögzíti).
4. **Settings → Environment Variables** (NEM `VITE_` prefixszel — ezek szerveroldaliak):
   - `AURI_SERVER_URL` = a Cloudflare Tunnel URL-je (pl. `https://auri.pelda.hu`)
   - `AURI_SERVER_API_KEY` = a `server`-ben `npm run generate-key`-jel gyártott kulcs
5. **Environment Variable a frontendnek** (ez mehet `VITE_`-vel, mert nem titok):
   - `VITE_API_URL` = `/api/chat`
6. Deploy. A böngésző a `/api/chat`-et hívja, a proxy (`api/chat.ts`) hozzáteszi a kulcsot
   és továbbít a tunnel-backendnek. **A kulcs sosem kerül a böngészőbe.**

### Hogyan kommunikálnak

```
Böngésző → POST /api/chat (kulcs NÉLKÜL)
        → Vercel serverless (api/chat.ts, AURI_SERVER_API_KEY = titok)
        → POST {AURI_SERVER_URL}/v1/chat  Authorization: Bearer …
        → Cloudflare Tunnel → server/ → Ollama
```

A backend nem fut Vercelen (az Ollama miatt lokális/VPS) — lásd [../server/README.md](../server/README.md).

## Deploy GitHub Pages-re (csak MOCK mód)

A Pages statikus, nincs serverless proxy, ezért ott a frontend **MOCK módban** fut
(remek a vizuál bemutatására). A repó tartalmaz egy workflow-t: `.github/workflows/deploy-pages.yml`.
Engedélyezd: GitHub repo → Settings → Pages → Source: GitHub Actions.

## Animáció-hangolás (hol állítgasd)

| Mit | Hol |
|-----|-----|
| Meddig „él" a friss szöveg (hossz-arányos) | [src/lib/auriState.ts](src/lib/auriState.ts) → `liveDurationMs()` |
| Állapot-színek / reaktor-sebesség | [src/lib/auriState.ts](src/lib/auriState.ts) → `STATE_PALETTE` |
| Glow-erő, scan-line, rács, belépő anim | [src/styles/hud.css](src/styles/hud.css) (`:root` + `@keyframes`) |
| Particle-szám, radar | [src/components/HudBackground.tsx](src/components/HudBackground.tsx) |
| Mock-válaszok (rövid/hosszú) | [src/lib/mockResponses.ts](src/lib/mockResponses.ts) |

`prefers-reduced-motion` esetén a flicker/particle/scan kikapcsol, a HUD statikus marad.

## Komponens-térkép

```
src/
  App.tsx                 állapotgép (idle/listening/thinking/speaking/error) + elrendezés
  components/
    HudBackground.tsx     canvas particle + radar
    ScanlineOverlay.tsx   scan-line + grain
    ArcReactor.tsx        állapotfüggő forgó reaktor (SVG)
    CornerHud.tsx         sarok-telemetria
    ChatPanel.tsx         üveg-panel + scroll
    ChatMessage.tsx       egy üzenet (user/auri)
    LiveText.tsx          a „megelevenedő", hossz-arányos szöveg
    ThinkingIndicator.tsx lüktető pontok + scan-gyűrű
    InputBar.tsx          beviteli mező + küldés
    SideWidgets.tsx       uptime / tokens / latency / load / vox
    SoundToggle.tsx       opcionális hangeffektek
  lib/  api.ts (mock+live+stream) · auriState.ts · mockResponses.ts · sound.ts · ui.ts
  hooks/ useLivePhase.ts
  api/chat.ts             Vercel serverless proxy (a TITKOS kulcs itt él)
```
