import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

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

// ── Fallback providers (mirror api/chat.ts so dev == prod) ───────────────────
interface Msg {
  role: string;
  content: string;
}
interface Fallbacks {
  groqKey: string;
  groqModel: string;
  geminiKey: string;
  geminiModel: string;
}
interface Completion {
  reply: string;
  model: string;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

const DEFAULT_SYSTEM =
  'Te Auri vagy, egy gyors és segítőkész AI-asszisztens. Válaszolj magyarul, tömören, ' +
  'barátságosan és lényegre törően. Ha a felhasználó más nyelven ír, azon a nyelven válaszolj.';

function withSystem(messages: Msg[]): Msg[] {
  return messages.some((m) => m.role === 'system')
    ? messages
    : [{ role: 'system', content: DEFAULT_SYSTEM }, ...messages];
}

async function callGroq(messages: Msg[], temperature: number | undefined, maxTokens: number | undefined, fb: Fallbacks): Promise<Completion | null> {
  if (!fb.groqKey) return null;
  try {
    const r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${fb.groqKey}` },
      body: JSON.stringify({ model: fb.groqModel, messages: withSystem(messages), temperature: temperature ?? 0.7, max_tokens: maxTokens ?? 1024 }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) return null;
    const j: any = await r.json();
    const reply: string = j.choices?.[0]?.message?.content ?? '';
    if (!reply) return null;
    const u = j.usage ?? {};
    return { reply, model: j.model ?? fb.groqModel, usage: { prompt_tokens: u.prompt_tokens ?? 0, completion_tokens: u.completion_tokens ?? 0, total_tokens: u.total_tokens ?? 0 } };
  } catch {
    return null;
  }
}

async function callGemini(messages: Msg[], temperature: number | undefined, maxTokens: number | undefined, fb: Fallbacks): Promise<Completion | null> {
  if (!fb.geminiKey) return null;
  const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n') || DEFAULT_SYSTEM;
  const contents = messages.filter((m) => m.role !== 'system').map((m) => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] }));
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${fb.geminiModel}:generateContent?key=${fb.geminiKey}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ systemInstruction: { parts: [{ text: sys }] }, contents, generationConfig: { temperature: temperature ?? 0.7, maxOutputTokens: maxTokens ?? 1024 } }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) return null;
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
        res.statusCode = 200;
        res.setHeader('content-type', 'application/json');
        res.setHeader('cache-control', 'no-store');
        res.end(JSON.stringify({ ollamaUp, models }));
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

        const ctrl = new AbortController();
        res.on('close', () => ctrl.abort());

        // 1) try the local Ollama server
        try {
          const upstream = await fetch(`${backendUrl}/v1/chat`, {
            method: 'POST',
            headers: { 'content-type': 'application/json', ...(backendKey ? { authorization: `Bearer ${backendKey}` } : {}) },
            body,
            signal: ctrl.signal,
          });
          const ct = upstream.headers.get('content-type') ?? 'application/json';
          if (upstream.ok && upstream.body && ct.includes('text/event-stream')) {
            res.statusCode = 200;
            res.setHeader('content-type', ct);
            res.setHeader('cache-control', 'no-cache, no-transform');
            res.setHeader('x-auri-source', 'ollama');
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
        let parsed: any = {};
        try {
          parsed = JSON.parse(body);
        } catch {
          /* ignore */
        }
        const messages: Msg[] = Array.isArray(parsed.messages) ? parsed.messages : [];
        const temperature = typeof parsed.temperature === 'number' ? parsed.temperature : undefined;
        const maxTokens = typeof parsed.max_tokens === 'number' ? parsed.max_tokens : undefined;

        const viaGroq = await callGroq(messages, temperature, maxTokens, fb);
        const result = viaGroq ?? (await callGemini(messages, temperature, maxTokens, fb));
        if (result) {
          res.statusCode = 200;
          res.setHeader('content-type', 'application/json');
          res.setHeader('x-auri-source', viaGroq ? 'groq' : 'gemini');
          res.end(JSON.stringify(result));
          return;
        }
        res.statusCode = 503;
        res.setHeader('content-type', 'application/json');
        res.end(JSON.stringify({ error: 'no_backend', message: 'Local server offline and no fallback available.' }));
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
    groqModel: env.GROQ_MODEL || 'llama-3.3-70b-versatile',
    geminiKey: env.GEMINI_API_KEY || '',
    geminiModel: env.GEMINI_MODEL || 'gemini-2.0-flash',
  };

  console.log(
    `[auri proxy] local -> ${backendUrl} | key ${backendKey ? '✓' : '✗'} | groq ${fb.groqKey ? '✓' : '✗'} | gemini ${fb.geminiKey ? '✓' : '✗'}`,
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
