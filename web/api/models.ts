// Same-origin availability probe for the model picker. Tells the browser whether
// the user's LOCAL Ollama backend is reachable right now (PC on) and, if so,
// which models are installed — without exposing the backend URL/key to the client.
//   GET /api/models -> { ollamaUp: boolean, models: string[] }
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(_req: VercelRequest, res: VercelResponse): Promise<void> {
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

  res.setHeader('cache-control', 'no-store');
  res.status(200).json({ ollamaUp, models });
}
