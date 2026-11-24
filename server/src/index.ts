import express, { type Request, type Response, type NextFunction } from 'express';
import cors from 'cors';
import { config, hasApiKeys } from './config';
import { logger } from './util/logger';
import { healthRouter } from './routes/health';
import { modelsRouter } from './routes/models';
import { chatRouter } from './routes/chat';
import { ttsRouter } from './routes/tts';
import { warmup } from './ollama';

export function buildApp() {
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', true); // correct req.ip behind Cloudflare Tunnel / proxies
  app.use(express.json({ limit: '8mb' })); // up to 4 compressed images per chat request

  // CORS only matters for browser callers; server-to-server needs none.
  if (config.allowedOrigins.length > 0) {
    app.use(
      cors({
        origin: config.allowedOrigins,
        methods: ['GET', 'POST'],
        allowedHeaders: ['Content-Type', 'Authorization', 'x-api-key'],
        exposedHeaders: ['X-Auri-Model'], // DIRECT-mode browsers may read which model answered
      }),
    );
  }

  app.use(healthRouter);
  app.use(modelsRouter);
  app.use(chatRouter);
  app.use(ttsRouter);

  // 404
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: 'not_found' });
  });

  // Error handler (must keep 4 args to be recognized by Express).
  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    if (err?.type === 'entity.parse.failed') {
      res.status(400).json({ error: 'invalid_json' });
      return;
    }
    if (err?.type === 'entity.too.large') {
      res.status(413).json({ error: 'payload_too_large' });
      return;
    }
    logger.error('unhandled', { msg: String(err?.message ?? err) });
    res.status(500).json({ error: 'internal_error' });
  });

  return app;
}

function main(): void {
  if (!hasApiKeys()) {
    logger.error(
      'No usable AURI_API_KEY configured. Run `npm run generate-key`, then start again.',
    );
    process.exit(1);
  }

  const app = buildApp();
  const server = app.listen(config.port, () => {
    logger.info(`Auri AI server listening on http://localhost:${config.port}`, {
      model: config.ollamaModel,
      ollamaUrl: config.ollamaUrl,
      keys: config.apiKeys.length,
      rateLimitPerMin: config.rateLimitPerMin,
      allowedOrigins: config.allowedOrigins.length ? config.allowedOrigins : '(none — server-to-server)',
      keepAlive: config.ollamaKeepAlive,
      maxConcurrency: config.maxConcurrency,
    });
  });

  // Preload the model so the first real request is fast. Non-blocking; if Ollama
  // isn't up yet it just logs and the model loads lazily on the first request.
  if (config.warmupOnBoot) {
    void warmup().then((ok) =>
      logger.info('warmup', { ok, model: config.ollamaModel, keepAlive: config.ollamaKeepAlive }),
    );
  }

  const shutdown = (sig: string) => {
    logger.info(`Received ${sig}, shutting down...`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000).unref();
  };
  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

// Only auto-start when run directly (so tests can import buildApp()).
if (require.main === module) {
  main();
}
