import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

// ── ElevenLabs monthly budget, SHARED with the Jarvis daemon (dev only) ─────────
// The user asked for a code-level monthly cap. The key can't read the account quota, so
// both spenders book into one ledger: auri-jarvis/data/voice/credits.json
// {"month": "YYYY-MM", "used": N}; budget = audio.yaml tts.elevenlabs.monthly_credit_budget.
// Same contract as auri_jarvis/tts/credits.py (AI-1): estimate 0.5 credit/char before the
// call, book the `character-cost` header after it, atomic write (temp file + rename).
const EL_LEDGER = resolve(here, '../auri-jarvis/data/voice/credits.json');
const EL_AUDIO_YAML = resolve(here, '../auri-jarvis/config/audio.yaml');

function ledgerMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function elBudget(): number {
  try {
    const m = /monthly_credit_budget:\s*(\d+)/.exec(readFileSync(EL_AUDIO_YAML, 'utf8'));
    return m ? Number(m[1]) : 2000;
  } catch {
    return 2000;
  }
}
function ledgerUsed(): number {
  try {
    const d = JSON.parse(readFileSync(EL_LEDGER, 'utf8')) as { month?: string; used?: number };
    return d.month === ledgerMonth() ? Number(d.used) || 0 : 0;
  } catch {
    return 0;
  }
}
function ledgerAllows(text: string): boolean {
  return ledgerUsed() + Math.ceil(text.length * 0.5) <= elBudget();
}
function ledgerAdd(credits: number): void {
  try {
    const used = ledgerUsed() + Math.max(0, Math.floor(credits));
    mkdirSync(dirname(EL_LEDGER), { recursive: true });
    const tmp = EL_LEDGER.replace(/\.json$/, `.${process.pid}.tmp`);
    writeFileSync(tmp, JSON.stringify({ month: ledgerMonth(), used }), 'utf8');
    renameSync(tmp, EL_LEDGER);
  } catch (e) {
    console.warn('[auri proxy] credit ledger write failed:', (e as Error).message);
  }
}

// Resolve the backend key for the LOCAL dev proxy. Priority:
//   1) AURI_SERVER_API_KEY from web/.env.local (if present)
//   2) read it straight from ../server/.env (the single source of truth)
function resolveBackendKey(fromEnv: string): string {
  if (fromEnv) return fromEnv;
  try {
    const txt = readFileSync(resolve(here, '../server/.env'), 'utf8');
    const line = txt.split(/\r?\n/).find((l) => l.startsWith('AURI_API_KEY='));
    if (line) return line.slice('AURI_API_KEY='.length).trim().split(',')[0].trim();
  } catch {
    /* server/.env not found — proxy will 401 until configured */
  }
  return '';
}

// ElevenLabs for the web voice (dev mirror of api/tts.ts). Priority: web/.env.local, then
// ../auri-jarvis/.env (the single local source of the key, shared with the Jarvis daemon).
// Values are never logged — only ✓/✗.
function resolveElevenLabs(env: Record<string, string>): { elKey: string; elVoice: string; elModel: string } {
  let file: Record<string, string> = {};
  try {
    const txt = readFileSync(resolve(here, '../auri-jarvis/.env'), 'utf8');
    for (const line of txt.split(/\r?\n/)) {
      const m = /^(ELEVENLABS_[A-Z_]+)=(.*)$/.exec(line.trim());
      if (m) file[m[1]] = m[2].trim().replace(/^["']|["']$/g, '');
    }
  } catch {
    file = {};
  }
  const pick = (k: string) => (env[k] || file[k] || '').trim();
  return {
    elKey: pick('ELEVENLABS_API_KEY'),
    elVoice: pick('ELEVENLABS_VOICE_ID') || 'onwK4e9ZLuTAKqWW03F9', // Daniel
    elModel: pick('ELEVENLABS_MODEL_ID') || 'eleven_flash_v2_5',
  };
}

// ── Fallback providers (mirror api/chat.ts so dev == prod) ───────────────────
interface Msg {
  role: string;
  content: string;
  images?: string[]; // user turns: data:image/…;base64 URLs
}
// Vision: images go first to the LOCAL server (its OLLAMA_VISION_MODEL, default gemma4:e2b —
// the picture never leaves this PC); hosted fallback only to paid Gemini (GEMINI_PAID=1, same
// rule as prod — the free tier is not allowed for EEA users) or an explicit GROQ_VISION_MODEL.
// Image bytes are never logged.
const hasImages = (messages: Msg[]): boolean => messages.some((m) => m.images?.length);
function splitDataUrl(url: string): { mime: string; data: string } | null {
  const m = /^data:(image\/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/]+=*)$/.exec(url);
  return m ? { mime: m[1], data: m[2] } : null;
}
function toOpenAi(messages: Msg[]): unknown[] {
  return messages.map((m) =>
    m.images?.length
      ? { role: m.role, content: [{ type: 'text', text: m.content }, ...m.images.map((url) => ({ type: 'image_url', image_url: { url } }))] }
      : { role: m.role, content: m.content },
  );
}
function toGeminiContents(messages: Msg[]): unknown[] {
  return messages
    .filter((m) => m.role !== 'system')
    .map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [
        { text: m.content },
        ...(m.images ?? []).flatMap((u) => {
          const img = splitDataUrl(u);
          return img ? [{ inlineData: { mimeType: img.mime, data: img.data } }] : [];
        }),
      ],
    }));
}
interface Fallbacks {
  groqKey: string;
  groqModel: string;
  groqVisionModel: string; // GROQ_VISION_MODEL — only this Groq model ever gets images
  geminiKey: string;
  geminiModel: string;
  geminiPaid: boolean; // GEMINI_PAID=1 — required before Gemini may receive images
  ollamaUrl: string; // dev-only direct vision route (OLLAMA_URL, default 127.0.0.1:11434)
  ollamaVisionModel: string; // OLLAMA_VISION_MODEL, default gemma4:e2b
  elKey: string; // ElevenLabs (web voice), see resolveElevenLabs
  elVoice: string;
  elModel: string;
}
interface Completion {
  reply: string;
  model: string;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

const DEFAULT_SYSTEM =
  'Te Auri vagy, egy gyors és segítőkész AI-asszisztens. Válaszolj magyarul, tömören, ' +
  'barátságosan és lényegre törően. Ha a felhasználó más nyelven ír, azon a nyelven válaszolj.';

// Providers retire models without notice — surface the real reason instead of a bare 503.
async function warnProvider(name: string, model: string, r: Response): Promise<void> {
  const detail = (await r.text().catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
  console.warn(`[auri proxy] ${name} (${model}) failed: HTTP ${r.status} ${detail}`);
}

function withSystem(messages: Msg[]): Msg[] {
  return messages.some((m) => m.role === 'system')
    ? messages
    : [{ role: 'system', content: DEFAULT_SYSTEM }, ...messages];
}

async function callGroq(messages: Msg[], temperature: number | undefined, maxTokens: number | undefined, fb: Fallbacks): Promise<Completion | null> {
  const model = hasImages(messages) ? fb.groqVisionModel : fb.groqModel;
  if (!fb.groqKey || !model) return null;
  try {
    const r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${fb.groqKey}` },
      body: JSON.stringify({ model, messages: toOpenAi(withSystem(messages)), temperature: temperature ?? 0.7, max_tokens: maxTokens ?? 1024 }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) {
      await warnProvider('groq', model, r);
      return null;
    }
    const j: any = await r.json();
    const reply: string = j.choices?.[0]?.message?.content ?? '';
    if (!reply) return null;
    const u = j.usage ?? {};
    return { reply, model: j.model ?? model, usage: { prompt_tokens: u.prompt_tokens ?? 0, completion_tokens: u.completion_tokens ?? 0, total_tokens: u.total_tokens ?? 0 } };
  } catch {
    return null;
  }
}

// Dev only: images straight to the local Ollama's vision model when the Auri server
// (localhost:8787) isn't running — so `pnpm run dev` alone can read a pasted screenshot,
// while text chat keeps its usual route. Same settings as the server: no hidden thinking,
// the Jarvis daemon's context (8192) so the already-loaded gemma4:e2b is reused.
async function callOllamaVision(messages: Msg[], temperature: number | undefined, maxTokens: number | undefined, fb: Fallbacks): Promise<Completion | null> {
  if (!hasImages(messages)) return null;
  const model = fb.ollamaVisionModel;
  // one retry: a model swap in Ollama (e.g. the Jarvis daemon re-warming) can fail a call
  for (let attempt = 0; attempt < 2; attempt++) {
    const done = await callOllamaVisionOnce(messages, temperature, maxTokens, fb, model);
    if (done) return done;
    await new Promise((r) => setTimeout(r, 1500));
  }
  return null;
}

async function callOllamaVisionOnce(
  messages: Msg[],
  temperature: number | undefined,
  maxTokens: number | undefined,
  fb: Fallbacks,
  model: string,
): Promise<Completion | null> {
  try {
    const r = await fetch(`${fb.ollamaUrl}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model,
        stream: false,
        think: false,
        keep_alive: '30m',
        options: { num_ctx: 8192, temperature: temperature ?? 0.7, num_predict: maxTokens ?? 1024 },
        messages: withSystem(messages).map((m) => ({
          role: m.role,
          content: m.content,
          ...(m.images?.length ? { images: m.images.flatMap((u) => splitDataUrl(u)?.data ?? []) } : {}),
        })),
      }),
      signal: AbortSignal.timeout(120_000),
    });
    if (!r.ok) {
      await warnProvider('ollama-vision', model, r);
      return null;
    }
    const j: any = await r.json();
    const reply: string = j.message?.content ?? '';
    if (!reply.trim()) return null;
    const p = j.prompt_eval_count ?? 0;
    const c = j.eval_count ?? 0;
    return { reply, model, usage: { prompt_tokens: p, completion_tokens: c, total_tokens: p + c } };
  } catch {
    return null; // Ollama not running / model missing → hosted vision fallback
  }
}

async function callGemini(messages: Msg[], temperature: number | undefined, maxTokens: number | undefined, fb: Fallbacks): Promise<Completion | null> {
  if (!fb.geminiKey || (hasImages(messages) && !fb.geminiPaid)) return null;
  const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n') || DEFAULT_SYSTEM;
  const contents = toGeminiContents(messages);
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${fb.geminiModel}:generateContent?key=${fb.geminiKey}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ systemInstruction: { parts: [{ text: sys }] }, contents, generationConfig: { temperature: temperature ?? 0.7, maxOutputTokens: maxTokens ?? 1024 } }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) {
      await warnProvider('gemini', fb.geminiModel, r);
      return null;
    }
    const j: any = await r.json();
    const reply: string = (j.candidates?.[0]?.content?.parts ?? []).map((p: any) => p.text ?? '').join('').trim();
    if (!reply) return null;
    const um = j.usageMetadata ?? {};
    return { reply, model: fb.geminiModel, usage: { prompt_tokens: um.promptTokenCount ?? 0, completion_tokens: um.candidatesTokenCount ?? 0, total_tokens: um.totalTokenCount ?? 0 } };
  } catch {
    return null;
  }
}

// Local dev proxy as a Vite middleware. Mirrors the production Vercel function
// (api/chat.ts): forward to the local Ollama server; if it's down, fall back to
// Groq then Gemini. The key never reaches the client.
function auriDevProxy(backendUrl: string, backendKey: string, fb: Fallbacks): Plugin {
  return {
    name: 'auri-dev-proxy',
    configureServer(server) {
      // Same-origin availability probe for the model picker (dev mirror of api/models.ts).
      server.middlewares.use('/api/models', async (_req, res) => {
        let ollamaUp = false;
        let models: string[] = [];
        try {
          const h = await fetch(`${backendUrl}/health`, { signal: AbortSignal.timeout(3000) });
          ollamaUp = h.ok && ((await h.json()) as { status?: string }).status === 'ok';
        } catch {
          ollamaUp = false;
        }
        if (ollamaUp) {
          try {
            const m = await fetch(`${backendUrl}/v1/models`, {
              headers: backendKey ? { authorization: `Bearer ${backendKey}` } : {},
              signal: AbortSignal.timeout(4000),
            });
            if (m.ok) {
              const j = (await m.json()) as { models?: { name?: string }[] };
              models = (j.models ?? []).map((x) => x.name ?? '').filter(Boolean);
            }
          } catch {
            /* ignore */
          }
        }
        const hosted = {
          groq: fb.groqKey ? fb.groqModel : null,
          gemini: fb.geminiKey ? fb.geminiModel : null,
        };
        res.statusCode = 200;
        res.setHeader('content-type', 'application/json');
        res.setHeader('cache-control', 'no-store');
        res.end(JSON.stringify({ ollamaUp, models, hosted }));
      });

      // Web search (dev mirror of api/search.ts) — keyless DuckDuckGo HTML.
      server.middlewares.use('/api/search', async (req, res) => {
        const sendJson = (obj: unknown) => {
          res.statusCode = 200;
          res.setHeader('content-type', 'application/json');
          res.setHeader('cache-control', 'no-store');
          res.end(JSON.stringify(obj));
        };
        if (req.method !== 'POST') return sendJson({ results: [] });
        const chunks: Buffer[] = [];
        for await (const c of req) chunks.push(c as Buffer);
        let query = '';
        let pagesWanted = 0;
        try {
          const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8')) as { query?: unknown; pages?: unknown };
          query = String(parsed.query ?? '');
          pagesWanted = Math.max(0, Math.min(3, Number(parsed.pages) || 0));
        } catch {
          query = '';
        }
        if (!query.trim()) return sendJson({ results: [], pages: [] });
        const clean = (s: string) =>
          s
            .replace(/<[^>]+>/g, '')
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#x27;/g, "'")
            .replace(/&#39;/g, "'")
            .replace(/&nbsp;/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        const realUrl = (href: string) => {
          const m = href.match(/[?&]uddg=([^&]+)/);
          if (m) {
            try {
              return decodeURIComponent(m[1]);
            } catch {
              return '';
            }
          }
          if (href.startsWith('//')) return `https:${href}`;
          return href.startsWith('http') ? href : '';
        };
        const htmlToText = (html: string) =>
          clean(
            html
              .replace(/<script[\s\S]*?<\/script>/gi, ' ')
              .replace(/<style[\s\S]*?<\/style>/gi, ' ')
              .replace(/<head[\s\S]*?<\/head>/gi, ' ')
              .replace(/<!--[\s\S]*?-->/g, ' ')
              .replace(/<(nav|footer|header|aside|form)[\s\S]*?<\/\1>/gi, ' '),
          );
        const fetchPageText = async (url: string): Promise<string> => {
          try {
            const r = await fetch(url, {
              headers: { 'user-agent': 'Mozilla/5.0 (compatible; AuriBrain/1)' },
              signal: AbortSignal.timeout(7000),
            });
            if (!r.ok) return '';
            const ct = r.headers.get('content-type') ?? '';
            if (!/text\/html|text\/plain|xml/i.test(ct)) return '';
            return htmlToText(await r.text()).slice(0, 4000);
          } catch {
            return '';
          }
        };
        try {
          const r = await fetch('https://html.duckduckgo.com/html/', {
            method: 'POST',
            headers: {
              'content-type': 'application/x-www-form-urlencoded',
              'user-agent': 'Mozilla/5.0 (compatible; AuriBrain/1)',
            },
            body: `q=${encodeURIComponent(query.slice(0, 256))}`,
            signal: AbortSignal.timeout(9000),
          });
          if (!r.ok) return sendJson({ results: [] });
          const html = await r.text();
          const snippets: string[] = [];
          const snipRe = /<a[^>]*class="result__snippet"[^>]*>([\s\S]*?)<\/a>/g;
          let sm: RegExpExecArray | null;
          while ((sm = snipRe.exec(html))) snippets.push(clean(sm[1]));
          const results: { title: string; url: string; snippet: string }[] = [];
          const linkRe = /<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
          let m: RegExpExecArray | null;
          let i = 0;
          while ((m = linkRe.exec(html)) && results.length < 6) {
            const url = realUrl(m[1]);
            const title = clean(m[2]);
            if (url && title) results.push({ title, url, snippet: snippets[i] ?? '' });
            i++;
          }
          let pages: string[] = [];
          if (pagesWanted > 0 && results.length) {
            pages = (
              await Promise.all(results.slice(0, pagesWanted).map((h) => fetchPageText(h.url)))
            ).filter((t) => t.length > 80);
          }
          sendJson({ results, pages });
        } catch (e) {
          sendJson({ results: [], error: (e as Error).message });
        }
      });

      server.middlewares.use('/api/chat', async (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.setHeader('content-type', 'application/json');
          res.end('{"error":"method_not_allowed"}');
          return;
        }

        const chunks: Buffer[] = [];
        for await (const c of req) chunks.push(c as Buffer);
        const body = Buffer.concat(chunks).toString('utf8');
        let parsed: any = {};
        try {
          parsed = JSON.parse(body);
        } catch {
          /* ignore */
        }
        // The picker can force one hosted provider (no local, no fallback); else Auto.
        const provider: 'groq' | 'gemini' | undefined =
          parsed.provider === 'groq' || parsed.provider === 'gemini' ? parsed.provider : undefined;

        const ctrl = new AbortController();
        res.on('close', () => ctrl.abort());

        // 1) try the local Ollama server (Auto / local models only). Images too: the server
        //    answers them with its local vision model (OLLAMA_VISION_MODEL).
        const withImages = Array.isArray(parsed.messages) && hasImages(parsed.messages as Msg[]);
        if (!provider || withImages) try {
          const upstream = await fetch(`${backendUrl}/v1/chat`, {
            method: 'POST',
            headers: { 'content-type': 'application/json', ...(backendKey ? { authorization: `Bearer ${backendKey}` } : {}) },
            body,
            signal: ctrl.signal,
          });
          const ct = upstream.headers.get('content-type') ?? 'application/json';
          const upstreamModel = upstream.headers.get('x-auri-model');
          if (upstream.ok && upstream.body && ct.includes('text/event-stream')) {
            res.statusCode = 200;
            res.setHeader('content-type', ct);
            res.setHeader('cache-control', 'no-cache, no-transform');
            res.setHeader('x-auri-source', 'ollama');
            if (upstreamModel) res.setHeader('x-auri-model', upstreamModel);
            const reader = upstream.body.getReader();
            const decoder = new TextDecoder();
            for (;;) {
              const { done, value } = await reader.read();
              if (done) break;
              res.write(decoder.decode(value, { stream: true }));
            }
            res.end();
            return;
          }
          if (upstream.ok) {
            res.statusCode = 200;
            res.setHeader('content-type', ct);
            res.setHeader('x-auri-source', 'ollama');
            res.end(await upstream.text());
            return;
          }
          // non-ok -> fall through to fallback
        } catch {
          /* local unreachable -> fall through to fallback */
        }

        // 2) fallback: Groq then Gemini
        if (res.headersSent) {
          res.end();
          return;
        }
        const messages: Msg[] = Array.isArray(parsed.messages) ? parsed.messages : [];
        const temperature = typeof parsed.temperature === 'number' ? parsed.temperature : undefined;
        const maxTokens = typeof parsed.max_tokens === 'number' ? parsed.max_tokens : undefined;

        const viaOllama = withImages ? await callOllamaVision(messages, temperature, maxTokens, fb) : null;
        const viaGroq = !viaOllama && provider !== 'gemini' ? await callGroq(messages, temperature, maxTokens, fb) : null;
        const result =
          viaOllama ?? viaGroq ?? (provider !== 'groq' ? await callGemini(messages, temperature, maxTokens, fb) : null);
        if (result) {
          res.statusCode = 200;
          res.setHeader('content-type', 'application/json');
          res.setHeader('x-auri-source', viaOllama ? 'ollama' : viaGroq ? 'groq' : 'gemini');
          res.setHeader('x-auri-model', result.model);
          res.end(JSON.stringify(result));
          return;
        }
        res.statusCode = 503;
        res.setHeader('content-type', 'application/json');
        res.end(
          JSON.stringify({
            error: 'no_backend',
            message: withImages
              ? 'A képhez látó modell kell: fusson az Ollama a gemma4:e2b modellel (ollama pull gemma4:e2b), vagy állíts be fizetős Geminit (GEMINI_PAID=1) / GROQ_VISION_MODEL-t.'
              : provider
                ? `${provider === 'groq' ? 'Groq' : 'Gemini'} is unavailable right now (missing API key, rate limit or model error).`
                : 'Local server offline and no fallback available.',
          }),
        );
      });

      // TTS — binary audio; local-only (browser Web Speech covers the offline case).
      server.middlewares.use('/api/tts', async (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.setHeader('content-type', 'application/json');
          res.end('{"error":"method_not_allowed"}');
          return;
        }

        const chunks: Buffer[] = [];
        for await (const c of req) chunks.push(c as Buffer);
        const body = Buffer.concat(chunks).toString('utf8');

        const ctrl = new AbortController();
        res.on('close', () => ctrl.abort());

        // 1) ElevenLabs first (mirror of api/tts.ts); any problem → Piper below.
        let text = '';
        try {
          const parsed = JSON.parse(body) as { text?: unknown };
          text = typeof parsed.text === 'string' ? parsed.text.trim() : '';
        } catch {
          /* ignore */
        }
        if (fb.elKey && text && text.length <= 600 && !ledgerAllows(text)) {
          console.warn('[auri proxy] elevenlabs monthly budget reached → Piper / browser voice');
        }
        if (fb.elKey && text && text.length <= 600 && ledgerAllows(text)) {
          try {
            const r = await fetch(
              `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(fb.elVoice)}?output_format=mp3_44100_64`,
              {
                method: 'POST',
                headers: { 'xi-api-key': fb.elKey, 'content-type': 'application/json', accept: 'audio/mpeg' },
                body: JSON.stringify({ text, model_id: fb.elModel }),
                signal: ctrl.signal,
              },
            );
            if (r.ok) {
              const audio = Buffer.from(await r.arrayBuffer());
              const cost = Number(r.headers.get('character-cost'));
              ledgerAdd(Number.isFinite(cost) && cost > 0 ? cost : Math.ceil(text.length * 0.5));
              res.statusCode = 200;
              res.setHeader('content-type', 'audio/mpeg');
              res.setHeader('cache-control', 'no-store');
              res.setHeader('x-auri-voice', 'elevenlabs');
              res.end(audio);
              return;
            }
            console.warn(`[auri proxy] elevenlabs HTTP ${r.status} → Piper fallback`);
          } catch {
            if (ctrl.signal.aborted) return;
          }
        }

        // 2) Piper on the local Auri server
        try {
          const upstream = await fetch(`${backendUrl}/v1/tts`, {
            method: 'POST',
            headers: { 'content-type': 'application/json', ...(backendKey ? { authorization: `Bearer ${backendKey}` } : {}) },
            body,
            signal: ctrl.signal,
          });
          const ct = upstream.headers.get('content-type') ?? 'application/octet-stream';
          res.statusCode = upstream.status;
          res.setHeader('content-type', ct);
          if (!upstream.ok) {
            res.end(await upstream.text());
            return;
          }
          res.setHeader('cache-control', 'no-store');
          res.end(Buffer.from(await upstream.arrayBuffer()));
        } catch (e) {
          if (!res.headersSent) {
            res.statusCode = 502;
            res.setHeader('content-type', 'application/json');
            res.end(JSON.stringify({ error: 'proxy_error', message: (e as Error).message }));
          } else {
            res.end();
          }
        }
      });
    },
  };
}

// `base: './'` keeps asset URLs relative so the build works on both Vercel and
// GitHub Pages.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.AURI_SERVER_URL || 'http://localhost:8787';
  const backendKey = resolveBackendKey(env.AURI_SERVER_API_KEY || '');
  const fb: Fallbacks = {
    groqKey: env.GROQ_API_KEY || '',
    groqModel: env.GROQ_MODEL || 'openai/gpt-oss-120b',
    groqVisionModel: env.GROQ_VISION_MODEL || '',
    geminiKey: env.GEMINI_API_KEY || '',
    geminiModel: env.GEMINI_MODEL || 'gemini-flash-lite-latest',
    geminiPaid: env.GEMINI_PAID === '1',
    ollamaUrl: (env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/+$/, ''),
    ollamaVisionModel: env.OLLAMA_VISION_MODEL || 'gemma4:e2b',
    ...resolveElevenLabs(env),
  };

  console.log(
    `[auri proxy] local -> ${backendUrl} | key ${backendKey ? '✓' : '✗'} | groq ${fb.groqKey ? '✓' : '✗'} | gemini ${fb.geminiKey ? '✓' : '✗'} | elevenlabs ${fb.elKey ? '✓' : '✗'}`,
  );

  return {
    plugins: [react(), auriDevProxy(backendUrl, backendKey, fb)],
    base: './',
    server: { port: 5173 },
    // Note: no manualChunks for the seed corpus — AI-1 dynamic-imports it in
    // seedCorpus, so Vite already lazy-splits it (and defers it past first paint),
    // which halves the startup bundle. A manualChunks split would be redundant.
    build: { outDir: 'dist', sourcemap: false },
  };
});
