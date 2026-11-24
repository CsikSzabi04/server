// Same-origin availability probe for the model picker. Tells the browser whether
// the user's LOCAL Ollama backend is reachable right now (PC on) and, if so,
// which models are installed — without exposing the backend URL/key to the client.
// Also reports which hosted model each provider will really call (null = no key).
//   GET /api/models -> { ollamaUp, models: string[], hosted: { groq, gemini } }
import type { VercelRequest, VercelResponse } from '@vercel/node';
// Origin check + rate limit (SECURITY.md §8): every probe pings the owner's PC.
import { guard } from './_guard.js';

// Keep in sync with DEFAULT_GROQ_MODEL / DEFAULT_GEMINI_MODEL in api/chat.ts.
const DEFAULT_GROQ_MODEL = 'openai/gpt-oss-120b';
const DEFAULT_GEMINI_MODEL = 'gemini-flash-lite-latest';

// Short cache: many visitors polling must not turn into many requests to the home tunnel.
const CACHE_MS = 15_000;
let cached: { at: number; body: unknown } | null = null;
/** Test hook: forget the cached probe result. */
export function resetModelsCache(): void {
  cached = null;
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  if (!(await guard(req, res, 'models', 'GET'))) return;
  if (cached && Date.now() - cached.at < CACHE_MS) {
    res.status(200).json(cached.body);
    return;
  }
  const hosted = {
    groq: process.env.GROQ_API_KEY ? process.env.GROQ_MODEL || DEFAULT_GROQ_MODEL : null,
    // Gemini only with a billing-enabled project (GEMINI_PAID=1): Google's terms allow
    // only Paid Services for API clients used by EEA users (see api/chat.ts geminiKey).
    gemini:
      process.env.GEMINI_API_KEY && process.env.GEMINI_PAID === '1'
        ? process.env.GEMINI_MODEL || DEFAULT_GEMINI_MODEL
        : null,
  };
  // Why a hosted provider is off (so the picker can say so instead of "no API key").
  const disabled: Record<string, string> = {};
  if (process.env.GEMINI_API_KEY && process.env.GEMINI_PAID !== '1') disabled.gemini = 'eea_paid_only';
  const base = process.env.AURI_SERVER_URL?.replace(/\/+$/, '');
  const key = process.env.AURI_SERVER_API_KEY;

  let ollamaUp = false;
  let models: string[] = [];

  if (base) {
    try {
      const h = await fetch(`${base}/health`, { signal: AbortSignal.timeout(3000) });
      ollamaUp = h.ok && ((await h.json()) as { status?: string }).status === 'ok';
    } catch {
      ollamaUp = false;
    }
    if (ollamaUp && key) {
      try {
        const m = await fetch(`${base}/v1/models`, {
          headers: { authorization: `Bearer ${key}` },
          signal: AbortSignal.timeout(4000),
        });
        if (m.ok) {
          const j = (await m.json()) as any;
          const list = (j.models ?? j.data ?? []) as any[];
          models = list.map((x) => x.name ?? x.model ?? x.id).filter(Boolean);
        }
      } catch {
        /* ignore — keep models empty */
      }
    }
  }

  const body = { ollamaUp, models, hosted, disabled };
  cached = { at: Date.now(), body };
  res.status(200).json(body);
}
