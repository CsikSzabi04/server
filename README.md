# Auri — privát, ingyenes AI (backend + élő HUD frontend)

Ez a repo **két** önálló, de együttműködő projektet tartalmaz:

```
d:\Server\
  server/   →  Auri AI-szerver  (Node/Express, Ollama wrapper, /v1/chat)   ── LOKÁLISAN / VPS-en fut
  web/      →  AuriGPT HUD       (Vite + React, J.A.R.V.I.S. stílusú chat) ── VERCELRE deployolva
  PublicFreeAI/  (Ollama telepítő — gitignore-olt, NEM megy gitre)
```

## Hogyan kommunikálnak (és mi a biztonsági lényeg)

```
  Böngésző (Vercel, statikus React)
     │  POST /api/chat            ← NINCS API-kulcs a kliensben!
     ▼
  Vercel Serverless proxy  (web/api/chat.ts)
     │  AURI_SERVER_API_KEY = Vercel env-változó (TITOK, szerveroldali)
     │  POST {AURI_SERVER_URL}/v1/chat   +  Authorization: Bearer <kulcs>
     ▼
  Cloudflare Tunnel  →  server/ (lokális Auri-szerver)  →  Ollama (localhost:11434)
```

**Miért proxy?** A Vite-ban minden `VITE_*` env-változó **beégetődik a publikus
kliens-bundle-be**. Ha a titkos kulcsot oda tennénk, bárki kiolvashatná a böngészőből.
Ezért a kulcs **csak a Vercel serverless függvényben** él (szerveroldal), a böngésző
pedig kulcs nélkül hívja a saját `/api/chat`-jét. Részletek: [web/README.md](web/README.md).

## Mi megy gitre, mi NEM

| ✅ Gitre | ❌ Soha gitre |
|---------|--------------|
| `server/` és `web/` forráskód | `**/.env` (valódi kulcsok) |
| `.env.example` fájlok (placeholder) | `**/node_modules/`, `dist/`, build |
| README-k, konfig | `PublicFreeAI/` (Ollama + OllamaSetup.exe, nagy bináris) |
| | Vercel-titkok (a Vercel dashboardba kerülnek) |

Mindezt a gyökér [.gitignore](.gitignore) kezeli.

## Gyors start

```bash
# 1) Backend (külön terminál) — lokálisan
cd server
npm install
npm run generate-key      # kiírja a titkos kulcsot (mentsd el!)
npm run dev               # http://localhost:8787

# 2) Frontend (másik terminál)
cd web
npm install
npm run dev               # http://localhost:5173  (alapból MOCK mód, backend nélkül is megy)
```

## Deploy dióhéjban

1. **Backend online tétele:** `server/` fut lokálisan (vagy ingyenes Oracle VPS-en),
   és `cloudflared tunnel --url http://localhost:8787` ad neki publikus HTTPS URL-t.
   Lásd: [server/README.md](server/README.md).
2. **Frontend Vercelre:** importáld a repót a Vercelre, **Root Directory = `web`**,
   majd add meg a Vercel env-változókat:
   - `AURI_SERVER_URL` = a Cloudflare Tunnel URL-je
   - `AURI_SERVER_API_KEY` = a `server`-ben generált titkos kulcs

   Részletes lépések: [web/README.md](web/README.md).

> A teljes rendszer **ingyenes**: lokális Ollama + kis nyílt modell + Cloudflare Tunnel
> + Vercel Hobby. Semmilyen fizetős AI-API vagy GPU-felhő nem kell.
