// Vercel Serverless proxy for AuriGPT chat — with automatic provider fallback.
//
// Priority chain (each step used only if the previous is unavailable):
//   1) LOCAL  — your own Ollama server (via AURI_SERVER_URL tunnel), used only
//               when it is reachable AND healthy right now (your PC is on).
//   2) GROQ   — free hosted API (smart, fast) when GROQ_API_KEY is set.
//   3) GEMINI — free hosted API when GEMINI_API_KEY is set.
//   (else 503 — the frontend can show its mock/offline state.)
//
// The browser never holds any key: it calls this same-origin function, which
// adds the right secret server-side. Set in the Vercel dashboard:
//   AURI_SERVER_URL, AURI_SERVER_API_KEY   (local Ollama via tunnel)
//   GROQ_API_KEY    [, GROQ_MODEL]          (fallback #1)
//   GEMINI_API_KEY  [, GEMINI_MODEL]        (fallback #2)
import type { VercelRequest, VercelResponse } from '@vercel/node';

interface Msg {
  role: string;
  content: string;
}
interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}
interface Completion {
  reply: string;
  model: string;
  usage: Usage;
}

// Keep Auri's persona consistent across all providers (matches the server's).
const DEFAULT_SYSTEM =
  'Te Auri vagy, egy gyors és segítőkész AI-asszisztens. Válaszolj magyarul, tömören, ' +
  'barátságosan és lényegre törően. Ha a felhasználó más nyelven ír, azon a nyelven válaszolj.';

function withSystem(messages: Msg[]): Msg[] {
  return messages.some((m) => m.role === 'system')
    ? messages
    : [{ role: 'system', content: DEFAULT_SYSTEM }, ...messages];
}

// Is the local Ollama server reachable AND ready (your PC on)? Fast 3s probe.
async function localHealthy(base: string): Promise<boolean> {
  try {
    const r = await fetch(`${base}/health`, { signal: AbortSignal.timeout(3000) });
    if (!r.ok) return false;
    const j = (await r.json()) as { status?: string };
    return j.status === 'ok';
  } catch {
    return false;
  }
}

interface Opts {
  temperature?: number;
  maxTokens?: number;
}

// ── Fallback #1: Groq (OpenAI-compatible) ────────────────────────────────────
async function callGroq(messages: Msg[], o: Opts): Promise<Completion | null> {
  const key = process.env.GROQ_API_KEY;
  if (!key) return null;
  const model = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
  try {
    const r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model,
        messages: withSystem(messages),
        temperature: o.temperature ?? 0.7,
        max_tokens: o.maxTokens ?? 1024,
      }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) return null;
    const j = (await r.json()) as any;
    const reply: string = j.choices?.[0]?.message?.content ?? '';
    if (!reply) return null;
    const u = j.usage ?? {};
    return {
      reply,
      model: j.model ?? model,
      usage: {
        prompt_tokens: u.prompt_tokens ?? 0,
        completion_tokens: u.completion_tokens ?? 0,
        total_tokens: u.total_tokens ?? 0,
      },
    };
  } catch {
    return null;
  }
}

// ── Fallback #2: Google Gemini ───────────────────────────────────────────────
async function callGemini(messages: Msg[], o: Opts): Promise<Completion | null> {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return null;
  const model = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
  const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n') || DEFAULT_SYSTEM;
  const contents = messages
    .filter((m) => m.role !== 'system')
    .map((m) => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] }));
  try {
    const r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: sys }] },
          contents,
          generationConfig: {
            temperature: o.temperature ?? 0.7,
            maxOutputTokens: o.maxTokens ?? 1024,
          },
        }),
        signal: AbortSignal.timeout(30_000),
      },
    );
    if (!r.ok) return null;
    const j = (await r.json()) as any;
    const reply: string = (j.candidates?.[0]?.content?.parts ?? [])
      .map((p: any) => p.text ?? '')
      .join('')
      .trim();
    if (!reply) return null;
    const um = j.usageMetadata ?? {};
    return {
      reply,
      model,
      usage: {
        prompt_tokens: um.promptTokenCount ?? 0,
        completion_tokens: um.candidatesTokenCount ?? 0,
        total_tokens: um.totalTokenCount ?? 0,
      },
    };
  } catch {
    return null;
  }
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method_not_allowed' });
    return;
  }

  const body = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, any>;
  const messages: Msg[] = Array.isArray(body.messages) ? body.messages : [];
  const wantsStream = body.stream === true;
  const opts: Opts = {
    temperature: typeof body.temperature === 'number' ? body.temperature : undefined,
    maxTokens: typeof body.max_tokens === 'number' ? body.max_tokens : undefined,
  };
  if (!messages.length) {
    res.status(400).json({ error: 'bad_request', message: 'messages required' });
    return;
  }

  const base = process.env.AURI_SERVER_URL?.replace(/\/+$/, '');
  const key = process.env.AURI_SERVER_API_KEY;

  // ── 1) LOCAL (your Ollama) — only if reachable + healthy right now ──────────
  if (base && key && (await localHealthy(base))) {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 60_000);
    res.on('close', () => ctrl.abort());
    try {
      const upstream = await fetch(`${base}/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      const ct = upstream.headers.get('content-type') ?? '';

      if (wantsStream && upstream.body && ct.includes('text/event-stream')) {
        res.status(200);
        res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
        res.setHeader('Cache-Control', 'no-cache, no-transform');
        res.setHeader('Connection', 'keep-alive');
        res.setHeader('X-Accel-Buffering', 'no');
        res.setHeader('X-Auri-Source', 'ollama');
        const reader = upstream.body.getReader();
        const decoder = new TextDecoder();
        try {
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            res.write(decoder.decode(value, { stream: true }));
          }
        } finally {
          try {
            await reader.cancel();
          } catch {
            /* noop */
          }
        }
        res.end();
        clearTimeout(timeout);
        return;
      }

      if (upstream.ok) {
        const text = await upstream.text();
        res.status(200);
        res.setHeader('Content-Type', ct || 'application/json');
        res.setHeader('X-Auri-Source', 'ollama');
        res.send(text);
        clearTimeout(timeout);
        return;
      }
      clearTimeout(timeout); // upstream error -> fall through to API fallback
    } catch {
      clearTimeout(timeout);
      if (res.headersSent) {
        res.end(); // stream broke mid-way — can't fall back cleanly
        return;
      }
      // else: fall through to fallback
    }
  }

  // ── 2) FALLBACK: Groq, then Gemini ─────────────────────────────────────────
  if (res.headersSent) return;
  const viaGroq = await callGroq(messages, opts);
  const result = viaGroq ?? (await callGemini(messages, opts));
  if (result) {
    res.status(200);
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('X-Auri-Source', viaGroq ? 'groq' : 'gemini');
    res.send(JSON.stringify(result));
    return;
  }

  res.status(503).json({
    error: 'no_backend',
    message: 'Local server offline and no fallback API configured/available.',
  });
}
