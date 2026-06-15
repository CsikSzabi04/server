import { Router } from 'express';
import { config } from '../config';
import { ping } from '../ollama';
import { piperAvailable } from '../piper';
import { inferenceLimiter } from '../util/concurrency';

// GET /health — PUBLIC (no API key). Lets CliMark / monitoring decide whether
// to route traffic here before spending it. Always returns 200 so the caller
// can read the body; "degraded" means the wrapper is up but Ollama is not.
export const healthRouter = Router();

const startedAt = Date.now();

healthRouter.get('/health', async (_req, res) => {
  const ollamaUp = await ping();
  res.status(200).json({
    status: ollamaUp ? 'ok' : 'degraded',
    model: config.ollamaModel,
    ollama: ollamaUp ? 'up' : 'down',
    tts: piperAvailable() ? 'up' : 'down',
    inflight: inferenceLimiter.inflight,
    queued: inferenceLimiter.queued,
    uptime: Math.floor((Date.now() - startedAt) / 1000),
  });
});
