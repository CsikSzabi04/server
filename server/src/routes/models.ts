import { Router } from 'express';
import { requireApiKey } from '../auth';
import { rateLimit } from '../util/rateLimit';
import { listModels, OllamaError } from '../ollama';

// GET /v1/models — PROTECTED. Proxies Ollama /api/tags. Handy for debugging
// which models are actually installed on the host.
export const modelsRouter = Router();

modelsRouter.get('/v1/models', requireApiKey, rateLimit, async (_req, res) => {
  try {
    const data = await listModels();
    res.json(data);
  } catch (e) {
    const status = e instanceof OllamaError ? e.status : 500;
    res.status(status).json({ error: 'ollama_unavailable' });
  }
});
