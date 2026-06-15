# Auri AI Server

Privát, **teljesen ingyenes** AI inferencia-szerver, amely egy helyben futó
[Ollama](https://ollama.com) modellt csomagol be egy vékony, **API-kulccsal védett**
HTTP-API mögé. Ezt a szervert a **CliMarkAI** marketing-automatizációs SaaS
„AuriGPT” / „Auri” asszisztense hívja meg új, ingyenes AI-providerként.

> **TL;DR**
> 1. `npm install`
> 2. `npm run generate-key` → kiírja a titkos kulcsot egy keretben (**mentsd el!**)
> 3. töltsd ki a `.env`-et, telepítsd az Ollamát + húzz le egy modellt
> 4. `npm run dev` → a `GET /health` 200-at ad
> 5. tedd publikussá Cloudflare Tunnellel
> 6. a generált kulcsot tedd a CliMark `AURI_SERVER_API_KEY` env-jébe

---

## 1. Mi ez, és hogyan illeszkedik a képbe?

A CliMarkAI „Auri” asszisztense ma több AI-providert hív sorban:
**Gemini 2.5 Flash → OpenAI gpt-4o-mini → beépített sablonválaszok**.
Ez a szerver ebbe a sorba kerül be új providerként, hogy legyen egy **korlátlan,
ingyenes** AI-háttér, amely nem függ fizetős API-któl.

```
   ┌─────────────────────────────┐         HTTPS + Bearer API-key        ┌──────────────────────────────┐
   │   CliMarkAI (a MÁSIK projekt)│  ───────────────────────────────────▶ │   EZ a projekt: Auri AI-szerver │
   │   AuriGPT chat backend       │   POST /v1/chat   { messages, ... }    │   (Node/Express wrapper)        │
   │   provider-sor egyik eleme   │  ◀─────────────────────────────────── │        │                        │
   └─────────────────────────────┘         { reply, usage, ... }          │        ▼                        │
                                                                          │   Ollama (localhost:11434)      │
                                                                          │   pl. llama3.2:3b / qwen2.5:3b  │
                                                                          └──────────────────────────────┘
```

**Biztonsági alapelv:** kifelé **csak** a kulccsal védett szerver-port (alapból `8787`)
látszik. Az Ollama portja (`11434`) **soha** nem publikus — csak a szerver éri el lokálisan.

---

## 2. Előfeltételek

- **Node.js 20+** (`node --version`)
- **Ollama** telepítve és futva
- Egy letöltött, kicsi modell (CPU-n is fut)

### Ollama telepítése

| OS | Lépés |
|----|-------|
| **Windows** (ez a gép) | Töltsd le: <https://ollama.com/download/windows>, telepítsd. Az „Ollama” a háttérben fut, és figyeli a `http://localhost:11434` címet. |
| **macOS** | <https://ollama.com/download/mac> vagy `brew install ollama` |
| **Linux / VPS** | `curl -fsSL https://ollama.com/install.sh \| sh` majd `sudo systemctl enable --now ollama` |

### Modell letöltése

```bash
ollama pull llama3.2:3b
```

Ellenőrzés (az Ollama fut-e és válaszol-e):

```bash
curl http://localhost:11434/api/tags
```

#### Ajánlott modellek (kicsi, ingyenes, CPU-barát)

| Modell | Méret | Mikor |
|--------|-------|-------|
| `llama3.2:3b` | ~2 GB | jó általános alap (default) |
| `qwen2.5:3b-instruct` | ~2 GB | **erősebb többnyelvűség (magyarul is jobb)** + utasításkövetés |
| `gemma2:2b` | ~1.6 GB | a leggyorsabb, gyengébb gépre |
| `phi3:mini` | ~2.3 GB | 3.8B, jó minőség kis méretben |

> **Tipp magyar használathoz:** ha a `llama3.2:3b` magyarul gyengén teljesít,
> válts `qwen2.5:3b-instruct`-ra — ez tapasztalatilag erősebb többnyelvűségben.
> Modellcsere kódmódosítás nélkül: lásd a [Modellcsere](#9-modellcsere) szakaszt.

---

## 3. Telepítés lépésről lépésre

```bash
# 1) függőségek
npm install

# 2) titkos kulcs generálása (létrehozza/frissíti a .env-et is)
npm run generate-key
#   -> a kulcs egyszer, keretben megjelenik. MENTSD EL.

# 3) nézd át a .env-et (modell, port, stb.) — lásd lentebb
# 4) fejlesztői mód (auto-reload)
npm run dev

# élesben:
npm run build && npm start
```

A `npm run dev` indulásakor a log valami ilyet ír:

```
[..] INFO  Auri AI server listening on http://localhost:8787 {"model":"llama3.2:3b",...}
```

Ellenőrzés:

```bash
curl http://localhost:8787/health
# {"status":"ok","model":"llama3.2:3b","ollama":"up","uptime":3}
```

Ha az Ollama nem fut, a `status` `"degraded"` lesz (a szerver akkor is él) —
így a CliMark eldöntheti, hogy ne küldjön ide forgalmat.

---

## 4. Az API-kulcs (a biztonság magja)

- A kulcsot a **`npm run generate-key`** gyártja: `auri_sk_` prefix + 48 url-safe karakter.
- Bekerül a `.env`-be `AURI_API_KEY=...` néven. **Az `.env` gitignore-olt** —
  a kulcs soha nem kerül gitbe, és a logokban is maszkolva jelenik meg
  (`auri_sk_****wxyz`).
- **Ezt a kulcsot kell a CliMark szerveroldali env-jébe tenni:**
  `AURI_SERVER_API_KEY=<a kulcs>`.
- Minden védett kérésnél a szerver `crypto.timingSafeEqual`-lal, időállandó módon
  hasonlít (SHA-256 digesteken, így a hossz sosem szivárogtat).
- **Kulcsrotáció:** több kulcs is megadható vesszővel:
  `AURI_API_KEY=auri_sk_uj,auri_sk_regi`. Így új kulcsra válthatsz anélkül, hogy a
  régi azonnal eltörne.

A kulcsot a CliMark **szerveroldali** kódja küldi (sosem a böngésző), tehát nem
kerül kliensoldali bundle-be.

---

## 5. Konfiguráció (`.env`)

| Változó | Default | Leírás |
|---------|---------|--------|
| `PORT` | `8787` | a szerver publikus portja (a tunnel ide mutasson, **ne** a 11434-re) |
| `AURI_API_KEY` | — | titkos kulcs(ok), vesszővel több is |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama címe (csak lokális!) |
| `OLLAMA_MODEL` | `llama3.2:3b` | alapértelmezett modell |
| `ALLOWED_ORIGINS` | — | CORS allow-list (csak böngészős híváshoz) |
| `RATE_LIMIT_PER_MIN` | `60` | kéréslimit kulcsonként/IP-nként (0 = ki) |
| `OLLAMA_TIMEOUT_MS` | `60000` | Ollama-hívás timeout |
| `LOG_PROMPTS` | `false` | logolja-e a teljes promptot (adatvédelem) |
| `MAX_MESSAGES` / `MAX_PROMPT_CHARS` | `100` / `24000` | input-limitek |

---

## 6. Végpont-referencia

### `GET /health` — publikus (kulcs nélkül)

```json
{ "status": "ok", "model": "llama3.2:3b", "ollama": "up", "uptime": 42 }
```

`status`: `"ok"` (Ollama elérhető) vagy `"degraded"` (a wrapper él, de az Ollama nem).

### `GET /v1/models` — védett

Az Ollama `/api/tags`-ját proxyzza (telepített modellek listája). Debughoz hasznos.

### `POST /v1/chat` — védett — **a fő végpont**

**Kérés:**

```json
{
  "messages": [
    { "role": "system", "content": "Te egy segítőkész asszisztens vagy." },
    { "role": "user", "content": "Írj egy rövid köszöntőt." }
  ],
  "model": "llama3.2:3b",
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}
```

A `model`, `temperature`, `max_tokens`, `stream` mind opcionális.
A `messages` kötelező és nem üres.

**Válasz (nem-streaming):**

```json
{
  "reply": "a modell teljes válasza szövegként",
  "model": "llama3.2:3b",
  "usage": { "prompt_tokens": 123, "completion_tokens": 456, "total_tokens": 579 },
  "finish_reason": "stop"
}
```

A `usage` az Ollama `prompt_eval_count` / `eval_count` mezőiből készül — ezt a
CliMark `logAiUsage` token-naplózója használja.

**Hibakódok:** `400` (rossz body / nincs `messages`), `401` (rossz/hiányzó kulcs),
`429` (rate limit), `503` (Ollama nem fut vagy lassú → a CliMark fallbackelhet).

### Streaming (SSE) — `stream: true`

`Content-Type: text/event-stream`. Az események:

```
data: {"delta":"Szia"}

data: {"delta":", mit"}

data: {"delta":" segíthetek?"}

data: {"usage":{"prompt_tokens":12,"completion_tokens":7,"total_tokens":19},"finish_reason":"stop"}

data: [DONE]
```

Ha a kliens lezárja a kapcsolatot, a szerver megszakítja az Ollama-hívást is.

### `POST /v1/embeddings` — *(jövőbeli bővítés)*

A CliMark tudásbázisához később hasznos lehet (`nomic-embed-text` modellel).
Az első körben **nincs implementálva**.

---

## 7. Publikussá tétel (ingyenesen)

A CliMark a felhőben fut (Vercel), tehát publikus URL-en kell elérnie ezt a
szervert. Fizetős GPU-felhő **nem kell** — a modell a saját gépeden fut CPU-n.

### Cloudflare Tunnel (ajánlott)

Ingyenes, stabil hostnév, nincs nyitott router-port, TLS adott. A tunnel a
**szerver portjára** (`8787`) mutasson, **soha** az Ollama `11434`-re.

```bash
# 1) cloudflared telepítése (Windows): https://github.com/cloudflare/cloudflared/releases
#    vagy: winget install --id Cloudflare.cloudflared

# 2) gyors teszt-tunnel (változó *.trycloudflare.com URL):
cloudflared tunnel --url http://localhost:8787

# --- vagy állandó, saját aldomainnel (Cloudflare-zónán) ---
cloudflared tunnel login
cloudflared tunnel create auri
# DNS route a saját domainedre:
cloudflared tunnel route dns auri auri.pelda-domain.hu
# config.yml (ingress) a 8787-re mutasson, majd:
cloudflared tunnel run auri
```

A kapott URL (pl. `https://auri.pelda-domain.hu`) lesz a CliMark `AURI_SERVER_URL`-je.

### Alternatívák

- **ngrok** (fejlesztéshez): `ngrok http 8787`. Ingyenes tieren változó URL —
  fejlesztésre jó, élesre kevésbé.
- **Ingyenes/olcsó VPS** (pl. **Oracle Cloud Always Free** ARM-instance):
  elbír egy 3B modellt CPU-n. Ott az Ollama + ez a szerver **együtt** fut,
  így **mindig elérhető** (nem csak amikor a saját géped megy).

| Megoldás | Mindig fut? | URL | Mikor |
|----------|-------------|-----|-------|
| Cloudflare Tunnel (otthoni gép) | csak amíg a géped megy | állandó | egyszerű, ingyenes |
| ngrok | csak amíg fut | változó (free) | fejlesztés |
| Oracle Free VPS | igen | állandó | „production-szerű”, mindig elérhető |

Bármelyiknél: **csak a kulccsal védett szerver-port legyen kívülről elérhető.**

---

## 8. CliMark-integráció (a másik projekt oldala)

A CliMarknak két új env-változó kell (lokálisan **és** a Vercelen):

```env
AURI_SERVER_URL=https://<a-cloudflare-tunnel-url>
AURI_SERVER_API_KEY=<a npm run generate-key által gyártott kulcs>
```

**Hova a provider-sorban?** Javasolt sorrend: a saját ingyenes szerver legyen az
**első** (vagy közvetlenül a Gemini után), mert ingyenes és korlátlan — és csak ha
a `/health` nem `ok`, vagy hiba/timeout van, essen tovább a meglévő láncra
(Gemini → OpenAI → sablon). Így nem nő a fizetős költség.

### Kész, bemásolható snippet (TypeScript)

Illeszd be a CliMark AI-provider moduljába, és tedd a provider-lánc elejére.
Hiba esetén `null`-t ad vissza, így a hívó tovább tud esni a fallbackre.

```ts
// climark: src/lib/ai/auriServer.ts
type ChatMessage = { role: 'system' | 'user' | 'assistant'; content: string };

export interface AuriResult {
  reply: string;
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  model?: string;
}

const BASE = process.env.AURI_SERVER_URL;
const KEY = process.env.AURI_SERVER_API_KEY;
const TIMEOUT_MS = 30_000;

/** Saját ingyenes Auri-szerver hívása. null = essünk tovább a fallbackre. */
export async function callAuriServer(messages: ChatMessage[]): Promise<AuriResult | null> {
  if (!BASE || !KEY) return null; // nincs konfigurálva -> skip

  // 1) gyors health-előellenőrzés, hogy ne pazaroljunk 30s-ot egy halott szerverre
  try {
    const h = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(3000) });
    const hj = (await h.json()) as { status?: string };
    if (hj.status !== 'ok') return null; // degraded/down -> fallback
  } catch {
    return null;
  }

  // 2) tényleges chat-hívás
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE}/v1/chat`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${KEY}`,
      },
      body: JSON.stringify({ messages, temperature: 0.7, max_tokens: 1024 }),
      signal: ctrl.signal,
    });

    if (!res.ok) return null; // 401/429/503 -> fallback
    const data = (await res.json()) as AuriResult;
    if (!data?.reply) return null;

    // logAiUsage(data.usage)  // <- a CliMark token-naplózója ide kötheti be
    return data;
  } catch {
    return null; // timeout / hálózati hiba -> fallback
  } finally {
    clearTimeout(t);
  }
}
```

A provider-láncban kb. így használd:

```ts
const auri = await callAuriServer(messages);
if (auri) return auri.reply;          // ingyenes, sikerült
// különben: Gemini -> OpenAI -> sablon (a meglévő lánc)
```

---

## 9. Modellcsere

```bash
ollama pull qwen2.5:3b-instruct      # új modell letöltése
# .env:  OLLAMA_MODEL=qwen2.5:3b-instruct
# majd a szerver újraindítása (npm run dev)
```

Kérésenként is felülírható a `model` mezővel a `POST /v1/chat` bodyban.

---

## 10. Tesztelés

```bash
# health
curl http://localhost:8787/health

# jó kulccsal (cseréld ki a kulcsot)
curl -X POST http://localhost:8787/v1/chat \
  -H "Authorization: Bearer auri_sk_XXXX" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Köszönj magyarul egy mondatban."}]}'

# rossz kulccsal -> 401
curl -i -X POST http://localhost:8787/v1/chat \
  -H "Authorization: Bearer rossz" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi"}]}'

# streaming
curl -N -X POST http://localhost:8787/v1/chat \
  -H "Authorization: Bearer auri_sk_XXXX" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Számolj 1-től 5-ig."}],"stream":true}'
```

Automata smoke-teszt (futó szerver mellett, külön terminálban):

```bash
npm run smoke
```

Ez ellenőrzi: `/health`, hiányzó kulcs → 401, rossz kulcs → 401, üres `messages`
→ 400, és ha az Ollama fut, egy valódi chat- + stream-hívást is.

---

## 11. Hibaelhárítás

| Tünet | Ok / megoldás |
|-------|---------------|
| `/health` → `"degraded"` | Az Ollama nem fut. Indítsd el (Windowson a háttéralkalmazás), `curl http://localhost:11434/api/tags`. |
| `503 model_unavailable` | Ollama nem elérhető vagy túl lassú. Növeld az `OLLAMA_TIMEOUT_MS`-t, vagy válts kisebb modellt (`gemma2:2b`). |
| `400 model_not_found` | A kért modell nincs letöltve: `ollama pull <modell>`. |
| `401 unauthorized` | Hiányzik/rossz a `Authorization: Bearer <kulcs>` (vagy `x-api-key`). Ellenőrizd a CliMark `AURI_SERVER_API_KEY`-jét. |
| `429 rate_limited` | Túllépted a `RATE_LIMIT_PER_MIN`-t. Emeld, vagy `0`-val kapcsold ki. |
| CORS-hiba böngészőből | Add a domaint az `ALLOWED_ORIGINS`-hoz. (Szerver-szerver hívásnál nem kell.) |
| Szerver nem indul: „No usable AURI_API_KEY” | Futtasd: `npm run generate-key`. |
| Lassú első válasz | A modell betöltése (load) az első hívásnál lassú; utána gyorsabb. |

---

## 12. Projektstruktúra

```
auri-ai-server/
  src/
    index.ts            # Express bootstrap, CORS, error-handler, graceful shutdown
    config.ts           # .env betöltés + validáció
    auth.ts             # API-key middleware (timingSafeEqual, több kulcs)
    ollama.ts           # Ollama kliens: chat + stream + tags + ping
    routes/
      health.ts         # GET  /health      (publikus)
      models.ts         # GET  /v1/models   (védett)
      chat.ts           # POST /v1/chat      (védett, fő végpont)
    util/
      logger.ts         # struktúrált log + kulcs-maszkolás
      rateLimit.ts      # egyszerű per-kulcs/IP rate limit
  scripts/
    generate-key.ts     # API-kulcs generálás + keretes kiírás + .env írás
    smoke.ts            # smoke teszt a fő végpontokra
  .env.example
  .gitignore
  package.json
  tsconfig.json
  README.md
```

## NPM scriptek

| Script | Mit csinál |
|--------|-----------|
| `npm run dev` | fejlesztői szerver auto-reloaddal (`tsx watch`) |
| `npm run build` | TypeScript fordítás `dist/`-be |
| `npm start` | a lefordított szerver futtatása (`node dist/src/index.js`) |
| `npm run typecheck` | `tsc --noEmit` (0 hiba a cél) |
| `npm run generate-key` | titkos kulcs generálás + `.env` |
| `npm run smoke` | smoke teszt futó szerver ellen |

---

*A teljes rendszer ingyenes: lokális Ollama + kis nyílt modell + Cloudflare Tunnel.
Semmilyen fizetős AI-API vagy GPU-felhő nem szükséges.*
