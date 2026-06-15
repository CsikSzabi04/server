import { Router } from 'express';
import { requireApiKey } from '../auth';
import { rateLimit } from '../util/rateLimit';
import { config } from '../config';
import { synthesize, piperAvailable, PiperError } from '../piper';
import { logger } from '../util/logger';

// POST /v1/tts — PROTECTED. Text-to-speech via local Piper.
// Body: { text, voice? }  ->  audio/wav (binary)
// 503 tts_unavailable if Piper isn't installed/configured (caller can fall back
// to browser Web Speech). Mirrors the chat route's auth + rate-limit + abort.
export const ttsRouter = Router();

ttsRouter.post('/v1/tts', requireApiKey, rateLimit, async (req, res) => {
  const started = Date.now();
  const body = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, unknown>;
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  const voice = typeof body.voice === 'string' && body.voice ? body.voice : undefined;

  if (!text) {
    res.status(400).json({ error: 'bad_request', message: 'text is required' });
    return;
  }
  if (text.length > config.piperMaxChars) {
    res.status(400).json({ error: 'text_too_long', message: `max ${config.piperMaxChars} chars` });
    return;
  }
  if (!piperAvailable()) {
    res.status(503).json({ error: 'tts_unavailable', message: 'Piper TTS is not installed/configured' });
    return;
  }

  const ctrl = new AbortController();
  res.on('close', () => {
    if (!res.writableFinished) ctrl.abort();
  });

  try {
    const wav = await synthesize({ text, voice, signal: ctrl.signal });
    res.status(200);
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('Content-Length', String(wav.length));
    res.setHeader('Cache-Control', 'no-store');
    res.end(wav);
    logger.info('tts', {
      chars: text.length,
      bytes: wav.length,
      durationMs: Date.now() - started,
      key: req.apiKeyMask,
    });
  } catch (e) {
    const status = e instanceof PiperError ? e.status : 500;
    if (!res.headersSent) {
      res.status(status).json({ error: 'tts_error', message: (e as Error).message });
    }
    logger.error('tts error', { msg: (e as Error).message, key: req.apiKeyMask });
  }
});
