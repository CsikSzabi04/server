// Vercel Serverless proxy for AuriGPT chat — with automatic provider fallback.
//
// Priority chain (each step used only if the previous is unavailable):
//   1) LOCAL  — your own Ollama server (via AURI_SERVER_URL tunnel), used only
//               when it is reachable AND healthy right now (your PC is on).
//   2) GROQ   — free hosted API (smart, fast) when GROQ_API_KEY is set.
//   3) GEMINI — hosted API when GEMINI_API_KEY is set AND GEMINI_PAID=1 (billing-
//               enabled project; Google's terms forbid the free quota for EEA users).
//   (else 503 — the frontend can show its mock/offline state.)
//
// The browser never holds any key: it calls this same-origin function, which
// adds the right secret server-side. Set in the Vercel dashboard:
//   AURI_SERVER_URL, AURI_SERVER_API_KEY   (local Ollama via tunnel)
//   GROQ_API_KEY    [, GROQ_MODEL]          (fallback #1)
//   GEMINI_API_KEY  [, GEMINI_MODEL]        (fallback #2)
import type { VercelRequest, VercelResponse } from '@vercel/node';
// Caller identification, rate limits, origin check, input validation (SECURITY.md §8).
import { guard, validateMessages, clamp } from './_guard.js';

interface Msg {
  role: string;
  content: string;
  images?: string[]; // user turns: data:image/…;base64 URLs (validated by _guard)
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
const DEFAULT_SYSTEM = `You are Auri — a sharp, fast, and genuinely helpful AI assistant.

How you answer:
- Reply in the user's language; default to English. Be concise, but never so
  short that the answer becomes wrong or unusable. Correctness first, brevity second.
- Read the question for INTENT, then give the most direct useful answer.

Use your memory (this is what makes you smart):
- The sections "What you know about the user" and "Relevant earlier info" below are
  REAL facts, preferences and document excerpts retrieved from your long-term memory
  about THIS specific user. Trust them and actively use them.
- Always ground your answer in that context when it is relevant. Prefer the user's
  own documents and stated facts over generic knowledge; if they conflict, follow the
  document/fact and briefly say so.
- For questions about an uploaded document, answer FROM the provided excerpts. If the
  excerpts don't contain the answer, say what's missing — never invent it.
- Connect the dots: combine several memory items + the user's preferences + the current
  question into one tailored answer, not a generic one.

Keep learning (get better every turn):
- Notice durable new facts, names, goals, preferences and corrections, and apply them
  to every following reply in this conversation.
- If the user corrects you, accept it instantly and stick to the corrected version.
- If something important is ambiguous or missing, ask ONE short clarifying question
  instead of guessing.

Honesty:
- Never fabricate. If memory doesn't cover it or you're unsure, say so plainly and
  offer the best next step.`;

// Default hosted models. Providers retire model IDs without notice (that silently
// broke llama-3.3-70b-versatile and gemini-2.0-flash), so the Gemini default is an
// auto-updating "-latest" alias, and every failure is logged with the real reason.
const DEFAULT_GROQ_MODEL = 'openai/gpt-oss-120b';
const DEFAULT_GEMINI_MODEL = 'gemini-flash-lite-latest';

async function warnProvider(name: string, model: string, r: Response): Promise<void> {
  const detail = (await r.text().catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
  console.warn(`[auri] ${name} (${model}) failed: HTTP ${r.status} ${detail}`);
}

// ── Vision (images on user turns) ────────────────────────────────────────────
// First the user's own local server (its vision model, OLLAMA_VISION_MODEL = gemma4:e2b);
// of the hosted providers only Gemini (paid, see geminiKey) or an explicitly configured
// Groq vision model ever receive images. Image bytes are never logged.
const hasImages = (messages: Msg[]): boolean => messages.some((m) => m.images?.length);

function splitDataUrl(url: string): { mime: string; data: string } | null {
  const m = /^data:(image\/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/]+=*)$/.exec(url);
  return m ? { mime: m[1], data: m[2] } : null;
}

/** OpenAI chat format: a turn with images becomes text + image_url content parts. */
function toOpenAi(messages: Msg[]): unknown[] {
  return messages.map((m) =>
    m.images?.length
      ? { role: m.role, content: [{ type: 'text', text: m.content }, ...m.images.map((url) => ({ type: 'image_url', image_url: { url } }))] }
      : { role: m.role, content: m.content },
  );
}

/** Gemini contents: text part + one inlineData part per image. */
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

/** The Groq model for this request; null when it has images but no vision model is set. */
function groqModelFor(messages: Msg[]): string | null {
  if (hasImages(messages)) return process.env.GROQ_VISION_MODEL || null;
  return process.env.GROQ_MODEL || DEFAULT_GROQ_MODEL;
}

function withSystem(messages: Msg[]): Msg[] {
  return messages.some((m) => m.role === 'system')
    ? messages
    : [{ role: 'system', content: DEFAULT_SYSTEM }, ...messages];
}

// Is the local Ollama server reachable AND ready (your PC on)? Fast probe so a
// sleeping PC doesn't stall the fallback to the hosted APIs.
async function localHealthy(base: string): Promise<boolean> {
  try {
    const r = await fetch(`${base}/health`, { signal: AbortSignal.timeout(1500) });
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
  const model = groqModelFor(messages);
  if (!key || !model) return null;
  try {
    const r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model,
        messages: toOpenAi(withSystem(messages)),
        temperature: o.temperature ?? 0.7,
        max_tokens: o.maxTokens ?? 1024,
      }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!r.ok) {
      await warnProvider('groq', model, r);
      return null;
    }
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
// LEGAL GATE (SECURITY.md §14.3, H-9): Google's Gemini API terms (effective
// 2026-03-23) say "You may use only Paid Services when making API Clients available
// to users in the European Economic Area, Switzerland, or the United Kingdom".
// AuriGPT serves EEA (Hungarian) users, so Gemini is used ONLY when the operator
// confirms a billing-enabled Cloud project with GEMINI_PAID=1. Otherwise: skipped.
function geminiKey(): string | undefined {
  return process.env.GEMINI_PAID === '1' ? process.env.GEMINI_API_KEY : undefined;
}

async function callGemini(messages: Msg[], o: Opts): Promise<Completion | null> {
  const key = geminiKey();
  if (!key) return null;
  const model = process.env.GEMINI_MODEL || DEFAULT_GEMINI_MODEL;
  const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n') || DEFAULT_SYSTEM;
  const contents = toGeminiContents(messages);
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
    if (!r.ok) {
      await warnProvider('gemini', model, r);
      return null;
    }
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

// ── Streaming variants: forward the provider's tokens to the browser as SSE ──
// Frontend (api.ts) parses `data: {"delta": "..."}` events, an optional
// `data: {"usage": {...}}`, then `data: [DONE]`. Each returns true once it has
// committed to streaming (response started); false if unavailable before then,
// so the caller can try the next provider.
function beginSse(res: VercelResponse, source: string, model: string): void {
  res.status(200);
  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.setHeader('X-Auri-Source', source);
  res.setHeader('X-Auri-Model', model); // the UI shows which model answered
}

async function pipeSse(
  body: ReadableStream<Uint8Array>,
  res: VercelResponse,
  pick: (obj: any) => { delta?: string; usage?: Usage },
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) >= 0) {
        const evt = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        for (const line of evt.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const data = trimmed.slice(5).trim();
          if (!data || data === '[DONE]') continue;
          try {
            const { delta, usage } = pick(JSON.parse(data));
            if (delta) res.write(`data: ${JSON.stringify({ delta })}\n\n`);
            if (usage) res.write(`data: ${JSON.stringify({ usage })}\n\n`);
          } catch {
            /* ignore partial / non-JSON keep-alives */
          }
        }
      }
    }
  } catch {
    /* upstream stream broke — close out cleanly below */
  }
  res.write('data: [DONE]\n\n');
  res.end();
}

async function streamGroq(messages: Msg[], o: Opts, res: VercelResponse): Promise<boolean> {
  const key = process.env.GROQ_API_KEY;
  const model = groqModelFor(messages);
  if (!key || !model) return false;
  let r: Response;
  try {
    r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model,
        messages: toOpenAi(withSystem(messages)),
        temperature: o.temperature ?? 0.7,
        max_tokens: o.maxTokens ?? 1024,
        stream: true,
        stream_options: { include_usage: true },
      }),
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    return false;
  }
  if (!r.ok || !r.body) {
    await warnProvider('groq', model, r);
    return false;
  }

  beginSse(res, 'groq', model);
  await pipeSse(r.body, res, (obj) => {
    const delta = obj.choices?.[0]?.delta?.content;
    const u = obj.usage;
    return {
      delta: typeof delta === 'string' ? delta : undefined,
      usage: u
        ? {
            prompt_tokens: u.prompt_tokens ?? 0,
            completion_tokens: u.completion_tokens ?? 0,
            total_tokens: u.total_tokens ?? 0,
          }
        : undefined,
    };
  });
  return true;
}

async function streamGemini(messages: Msg[], o: Opts, res: VercelResponse): Promise<boolean> {
  const key = geminiKey();
  if (!key) return false;
  const model = process.env.GEMINI_MODEL || DEFAULT_GEMINI_MODEL;
  const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n') || DEFAULT_SYSTEM;
  const contents = toGeminiContents(messages);
  let r: Response;
  try {
    r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${key}`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: sys }] },
          contents,
          generationConfig: { temperature: o.temperature ?? 0.7, maxOutputTokens: o.maxTokens ?? 1024 },
        }),
        signal: AbortSignal.timeout(60_000),
      },
    );
  } catch {
    return false;
  }
  if (!r.ok || !r.body) {
    await warnProvider('gemini', model, r);
    return false;
  }

  beginSse(res, 'gemini', model);
  await pipeSse(r.body, res, (obj) => {
    const delta = (obj.candidates?.[0]?.content?.parts ?? []).map((p: any) => p.text ?? '').join('');
    const um = obj.usageMetadata;
    return {
      delta: delta || undefined,
      usage: um
        ? {
            prompt_tokens: um.promptTokenCount ?? 0,
            completion_tokens: um.candidatesTokenCount ?? 0,
            total_tokens: um.totalTokenCount ?? 0,
          }
        : undefined,
    };
  });
  return true;
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  // POST only, own origin, caller identified, within rate limits — else already answered.
  if (!(await guard(req, res, 'chat'))) return;

  const body = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, any>;
  const checked = validateMessages(body.messages); // roles whitelisted, count + size capped
  if (!checked.ok) {
    res.status(400).json({ error: 'bad_request', message: checked.error });
    return;
  }
  const messages: Msg[] = checked.messages;
  const wantsStream = body.stream === true;
  const opts: Opts = {
    temperature: clamp(body.temperature, 0, 2),
    maxTokens: clamp(body.max_tokens, 1, 4096),
  };
  // Only known, validated fields go on to the local server (never the raw body).
  const forward = {
    messages,
    stream: wantsStream,
    temperature: opts.temperature,
    max_tokens: opts.maxTokens,
    model: typeof body.model === 'string' ? body.model.slice(0, 120) : undefined,
  };

  const base = process.env.AURI_SERVER_URL?.replace(/\/+$/, '');
  const key = process.env.AURI_SERVER_API_KEY;
  // The picker can force one hosted provider (no local, no fallback); else Auto.
  const provider: 'groq' | 'gemini' | undefined =
    body.provider === 'groq' || body.provider === 'gemini' ? body.provider : undefined;
  const images = hasImages(messages);
  const noBackend = images
    ? 'A képhez látó modell kell: a helyi Auri-szerver (gemma4:e2b) most nem érhető el, és nincs fizetős Gemini (GEMINI_PAID=1) vagy GROQ_VISION_MODEL.'
    : provider
      ? `${provider === 'groq' ? 'Groq' : 'Gemini'} is unavailable right now (missing API key, rate limit or model error).`
      : 'Local server offline and no fallback API configured/available.';

  // ── 1) LOCAL (your Ollama) — only if reachable + healthy right now ──────────
  // Images too: the server answers them with its local vision model (OLLAMA_VISION_MODEL,
  // default gemma4:e2b) — the picture stays on the user's own machine. A forced hosted
  // provider is ignored for images (only a vision model can read them).
  if ((!provider || images) && base && key && (await localHealthy(base))) {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 60_000);
    res.on('close', () => ctrl.abort());
    try {
      const upstream = await fetch(`${base}/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify(forward),
        signal: ctrl.signal,
      });
      const ct = upstream.headers.get('content-type') ?? '';
      const upstreamModel = upstream.headers.get('x-auri-model');

      if (wantsStream && upstream.body && ct.includes('text/event-stream')) {
        res.status(200);
        res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
        res.setHeader('Cache-Control', 'no-cache, no-transform');
        res.setHeader('Connection', 'keep-alive');
        res.setHeader('X-Accel-Buffering', 'no');
        res.setHeader('X-Auri-Source', 'ollama');
        if (upstreamModel) res.setHeader('X-Auri-Model', upstreamModel);
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

  // Streaming clients: forward real SSE so the text appears token-by-token
  // instead of waiting for the whole reply. Each helper only commits once its
  // upstream responds OK, so we can still try the next provider before then.
  const useGroq = provider !== 'gemini';
  const useGemini = provider !== 'groq';

  if (wantsStream) {
    if (useGroq && (await streamGroq(messages, opts, res))) return;
    if (res.headersSent) return;
    if (useGemini && (await streamGemini(messages, opts, res))) return;
    if (res.headersSent) return;
    res.status(503).json({ error: 'no_backend', message: noBackend });
    return;
  }

  // Non-streaming clients (e.g. the document summariser): plain JSON.
  const viaGroq = useGroq ? await callGroq(messages, opts) : null;
  const result = viaGroq ?? (useGemini ? await callGemini(messages, opts) : null);
  if (result) {
    res.status(200);
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('X-Auri-Source', viaGroq ? 'groq' : 'gemini');
    res.setHeader('X-Auri-Model', result.model);
    res.send(JSON.stringify(result));
    return;
  }

  res.status(503).json({ error: 'no_backend', message: noBackend });
}
