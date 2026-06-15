// Vercel Serverless proxy for the Auri TTS backend (Piper).
//
// Same secret-key pattern as api/chat.ts: the browser calls this same-origin
// function with no key; this function adds the Bearer key from a server-side
// env var and forwards to the backend /v1/tts, returning the binary audio.
//
// Set in the Vercel dashboard (Project → Settings → Environment Variables):
//   AURI_SERVER_URL      = https://<your-cloudflare-tunnel>
//   AURI_SERVER_API_KEY  = auri_sk_...
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method_not_allowed' });
    return;
  }

  const base = process.env.AURI_SERVER_URL?.replace(/\/+$/, '');
  const key = process.env.AURI_SERVER_API_KEY;
  if (!base || !key) {
    res.status(503).json({
      error: 'not_configured',
      message: 'Set AURI_SERVER_URL and AURI_SERVER_API_KEY in the Vercel environment.',
    });
    return;
  }

  const body = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, unknown>;

  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), 60_000);
  res.on('close', () => ctrl.abort());

  try {
    const upstream = await fetch(`${base}/v1/tts`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });

    const ct = upstream.headers.get('content-type') ?? 'application/octet-stream';
    if (!upstream.ok) {
      // forward the JSON error verbatim so the client can fall back gracefully
      const text = await upstream.text();
      res.status(upstream.status);
      res.setHeader('Content-Type', ct);
      res.send(text);
      return;
    }

    const buf = Buffer.from(await upstream.arrayBuffer());
    res.status(200);
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('Cache-Control', 'no-store');
    res.send(buf);
  } catch (e) {
    const aborted = ctrl.signal.aborted;
    if (!res.headersSent) {
      res.status(aborted ? 504 : 502).json({
        error: aborted ? 'upstream_timeout' : 'upstream_error',
        message: aborted ? 'TTS backend did not respond in time.' : (e as Error).message,
      });
    } else {
      res.end();
    }
  } finally {
    clearTimeout(timeout);
  }
}
