// Vercel Serverless proxy for AuriGPT's spoken voice.
//
// Order: 1) ElevenLabs (premium voice, Daniel by default) when ELEVENLABS_API_KEY is set,
//        2) the Auri TTS backend (Piper) via the tunnel,
//        3) any non-OK answer → the browser falls back to its own Web Speech voice.
//
// Same secret-key pattern as api/chat.ts: the browser calls this same-origin function with
// no key; the keys live only in server-side env vars. Set in Vercel (Project → Settings →
// Environment Variables):
//   ELEVENLABS_API_KEY   = <key with Text-to-Speech permission; set a monthly credit limit on it!>
//   ELEVENLABS_VOICE_ID  = onwK4e9ZLuTAKqWW03F9 (Daniel, default) · JBFqnCBsd6RMkjVDRZzb (George)
//   ELEVENLABS_MODEL_ID  = eleven_flash_v2_5 (default; fast, multilingual incl. Hungarian)
//   AURI_SERVER_URL      = https://<your-cloudflare-tunnel>   (Piper fallback)
//   AURI_SERVER_API_KEY  = auri_sk_...
import type { VercelRequest, VercelResponse } from '@vercel/node';
// Caller identification, rate limits, origin check (SECURITY.md §8).
import { guard } from './_guard.js';

const DEFAULT_VOICE = 'onwK4e9ZLuTAKqWW03F9'; // Daniel (same as the Jarvis default)
const DEFAULT_MODEL = 'eleven_flash_v2_5';
const EL_MAX_CHARS = 600; // one sentence per request from the client; caps credit spend per call

/** ElevenLabs TTS → MP3 bytes, or null on any problem (no key, quota, network). The text is
 *  the only thing sent; the voice id comes from our env, never from the caller. */
async function elevenlabs(text: string, signal: AbortSignal): Promise<Buffer | null> {
  const key = process.env.ELEVENLABS_API_KEY?.trim();
  if (!key || text.length > EL_MAX_CHARS) return null;
  const voice = (process.env.ELEVENLABS_VOICE_ID || DEFAULT_VOICE).trim();
  const model = (process.env.ELEVENLABS_MODEL_ID || DEFAULT_MODEL).trim();
  try {
    const r = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(voice)}?output_format=mp3_44100_64`,
      {
        method: 'POST',
        headers: { 'xi-api-key': key, 'content-type': 'application/json', accept: 'audio/mpeg' },
        body: JSON.stringify({ text, model_id: model }),
        signal,
      },
    );
    if (!r.ok) {
      // Status only (quota / auth problems show up here) — never the key or the text.
      console.warn(`[tts] elevenlabs HTTP ${r.status} → falling back`);
      await r.text().catch(() => '');
      return null;
    }
    return Buffer.from(await r.arrayBuffer());
  } catch {
    return null;
  }
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  // POST only, own origin, caller identified, within rate limits — else already answered.
  if (!(await guard(req, res, 'tts'))) return;

  const raw = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, unknown>;
  // Forward only the fields the TTS server understands, size-capped.
  const text = typeof raw.text === 'string' ? raw.text.trim() : '';
  if (!text || text.length > 1200) {
    res.status(400).json({ error: 'bad_request', message: 'text is required (max 1200 chars)' });
    return;
  }

  // 1) ElevenLabs (premium voice)
  {
    const ctrlEl = new AbortController();
    const t = setTimeout(() => ctrlEl.abort(), 15_000);
    res.on('close', () => ctrlEl.abort());
    const mp3 = await elevenlabs(text, ctrlEl.signal);
    clearTimeout(t);
    if (mp3) {
      res.status(200);
      res.setHeader('Content-Type', 'audio/mpeg');
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('X-Auri-Voice', 'elevenlabs');
      res.send(mp3);
      return;
    }
  }

  // 2) Piper on the Auri backend
  const base = process.env.AURI_SERVER_URL?.replace(/\/+$/, '');
  const key = process.env.AURI_SERVER_API_KEY;
  if (!base || !key) {
    res.status(503).json({
      error: 'not_configured',
      message: 'No voice backend: set ELEVENLABS_API_KEY, or AURI_SERVER_URL + AURI_SERVER_API_KEY.',
    });
    return;
  }
  // `voice` is deliberately NOT forwarded: the app never sends it, and the backend must not
  // receive caller-chosen file names (SECURITY.md §8). The server uses its default voice.
  const body = { text };

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

    if (!upstream.ok) {
      // Generic error only: the backend's message can contain local paths / tool output.
      // The client falls back to the browser's own voice on any non-OK status anyway.
      await upstream.text().catch(() => '');
      res.status(upstream.status >= 400 && upstream.status < 600 ? upstream.status : 502).json({ error: 'tts_failed' });
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
        message: aborted ? 'TTS backend did not respond in time.' : 'TTS backend unreachable.',
      });
    } else {
      res.end();
    }
  } finally {
    clearTimeout(timeout);
  }
}
