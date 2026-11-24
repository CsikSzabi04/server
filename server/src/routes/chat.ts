import { Router } from 'express';
import { requireApiKey } from '../auth';
import { rateLimit } from '../util/rateLimit';
import { config } from '../config';
import { chat, chatStream, OllamaError, type ChatMessage } from '../ollama';
import { inferenceLimiter } from '../util/concurrency';
import { logger } from '../util/logger';

// POST /v1/chat — PROTECTED. The main endpoint.
// Body: { messages, model?, temperature?, max_tokens?, stream? }
// A user message may carry `images`: up to 4 image data: URLs (png/jpeg/webp/gif) → the
// request is answered by the local vision model (OLLAMA_VISION_MODEL, default gemma4:e2b).
// Images never leave this machine and are never logged.
// Non-stream -> { reply, model, usage, finish_reason }
// stream:true -> Server-Sent Events: data:{"delta":...}, then data:{"usage":...},
//                then data:[DONE]
export const chatRouter = Router();

type ValidationResult =
  | { ok: true; messages: ChatMessage[]; images: number }
  | { ok: false; error: string };

const IMAGE_DATA_URL = /^data:image\/(?:png|jpeg|webp|gif);base64,([A-Za-z0-9+/]+=*)$/;
export const MAX_IMAGES = 4;
const MAX_IMAGE_CHARS = 1_500_000;
const MAX_IMAGES_TOTAL_CHARS = 6_000_000;

function validate(body: unknown): ValidationResult {
  if (!body || typeof body !== 'object') return { ok: false, error: 'invalid body' };
  const messages = (body as Record<string, unknown>).messages;

  if (!Array.isArray(messages) || messages.length === 0) {
    return { ok: false, error: 'messages must be a non-empty array' };
  }
  if (messages.length > config.maxMessages) {
    return { ok: false, error: `too many messages (max ${config.maxMessages})` };
  }

  let totalChars = 0;
  let imageCount = 0;
  let imageChars = 0;
  const clean: ChatMessage[] = [];
  for (const m of messages) {
    if (
      !m ||
      typeof m !== 'object' ||
      typeof (m as ChatMessage).role !== 'string' ||
      typeof (m as ChatMessage).content !== 'string'
    ) {
      return { ok: false, error: 'each message needs a string role and content' };
    }
    const { role, content } = m as ChatMessage;
    const images = (m as Record<string, unknown>).images;
    totalChars += content.length;
    // Only role + content (+ checked images) reach Ollama — no other fields pass through.
    const out: ChatMessage = { role, content };
    if (images !== undefined) {
      if (role !== 'user' || !Array.isArray(images)) return { ok: false, error: 'invalid images' };
      const raw: string[] = [];
      for (const img of images) {
        const match = typeof img === 'string' && img.length <= MAX_IMAGE_CHARS ? IMAGE_DATA_URL.exec(img) : null;
        if (!match) return { ok: false, error: 'invalid image (png/jpeg/webp/gif data URL, ≤1.5M chars)' };
        imageChars += img.length;
        raw.push(match[1]);
      }
      imageCount += raw.length;
      if (raw.length) out.images = raw;
    }
    clean.push(out);
  }
  if (totalChars > config.maxPromptChars) {
    return { ok: false, error: `prompt too large (max ${config.maxPromptChars} chars)` };
  }
  if (imageCount > MAX_IMAGES) return { ok: false, error: `too many images (max ${MAX_IMAGES})` };
  if (imageChars > MAX_IMAGES_TOTAL_CHARS) return { ok: false, error: 'images too large' };

  return { ok: true, messages: clean, images: imageCount };
}

// Prepend the default persona when the caller didn't supply a system message.
// This makes small models noticeably more coherent and on-task.
function withSystemPrompt(messages: ChatMessage[]): ChatMessage[] {
  if (!config.systemPrompt) return messages;
  if (messages.some((m) => m.role === 'system')) return messages;
  return [{ role: 'system', content: config.systemPrompt }, ...messages];
}

chatRouter.post('/v1/chat', requireApiKey, rateLimit, async (req, res) => {
  const started = Date.now();
  const keyMask = req.apiKeyMask;

  const v = validate(req.body);
  if (!v.ok) {
    res.status(400).json({ error: 'bad_request', message: v.error });
    return;
  }

  const body = req.body as Record<string, any>;
  // With images the request needs a vision model, whatever the picker asked for.
  const model =
    v.images > 0
      ? config.ollamaVisionModel
      : typeof body.model === 'string' && body.model
        ? body.model
        : config.ollamaModel;
  const temperature = typeof body.temperature === 'number' ? body.temperature : undefined;
  const maxTokens = typeof body.max_tokens === 'number' ? body.max_tokens : undefined;
  const stream = body.stream === true;

  // Abort on client disconnect — covers both the queue wait and the inference.
  const ctrl = new AbortController();
  res.on('close', () => {
    if (!res.writableFinished) ctrl.abort();
  });

  // Concurrency gate: serialize CPU-bound inference, fail fast when overloaded.
  const acq = inferenceLimiter.acquire(ctrl.signal);
  if (acq === null) {
    res.setHeader('Retry-After', '2');
    res.status(503).json({
      error: 'server_busy',
      message: 'Too many concurrent requests — retry shortly.',
      retry_after: 2,
    });
    return;
  }
  let release: () => void = () => {};
  try {
    release = await acq;
  } catch {
    return; // client disconnected while queued
  }
  const queuedMs = Date.now() - started;

  // Timeout covers only the inference itself, not time spent waiting in queue.
  // Reading an image on CPU (+ a possible model load) takes longer than a text reply.
  const timeoutMs = v.images > 0 ? Math.max(config.ollamaTimeoutMs, 120_000) : config.ollamaTimeoutMs;
  const timeout = setTimeout(() => ctrl.abort(), timeoutMs);

  const messages = withSystemPrompt(v.messages);
  if (config.logPrompts) {
    // never log image bytes — only how many there were
    logger.info('prompt', {
      model,
      messages: messages.map((m) => (m.images ? { ...m, images: `[${m.images.length} image(s)]` } : m)),
    });
  }

  const vision = v.images > 0 ? { numCtx: config.ollamaVisionNumCtx, think: false } : {};
  const params = { messages, model, temperature, maxTokens, signal: ctrl.signal, ...vision };

  // ── Streaming branch ──────────────────────────────────────────────────────
  if (stream) {
    // Defer SSE headers until the first chunk arrives. That way a connection
    // error (e.g. Ollama down) before any data can still return a proper HTTP
    // status instead of a half-open event stream.
    let headersSent = false;
    const ensureHeaders = () => {
      if (headersSent) return;
      res.status(200);
      res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache, no-transform');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no'); // disable proxy buffering (nginx)
      res.setHeader('X-Auri-Model', model); // the UI shows which model answered
      res.flushHeaders?.();
      headersSent = true;
    };

    let tokens = 0;
    let ttftMs = 0; // time-to-first-token (perceived speed)
    try {
      for await (const chunk of chatStream(params)) {
        ensureHeaders();
        if (chunk.delta) {
          if (!ttftMs) ttftMs = Date.now() - started;
          res.write(`data: ${JSON.stringify({ delta: chunk.delta })}\n\n`);
        }
        if (chunk.done) {
          tokens = chunk.usage?.total_tokens ?? 0;
          res.write(
            `data: ${JSON.stringify({ usage: chunk.usage, finish_reason: chunk.finish_reason })}\n\n`,
          );
        }
      }
      ensureHeaders();
      res.write('data: [DONE]\n\n');
      res.end();
    } catch (e) {
      const msg = (e as Error).message;
      if (!headersSent) {
        // Nothing streamed yet — respond with a real status code.
        if (e instanceof OllamaError && e.status === 404) {
          res.status(400).json({ error: 'model_not_found', message: msg });
        } else {
          res.status(503).json({ error: 'model_unavailable', message: msg });
        }
      } else {
        // Already streaming — surface the error as an event, then close.
        res.write(`data: ${JSON.stringify({ error: 'stream_error', message: msg })}\n\n`);
        res.end();
      }
      logger.error('stream error', { msg, key: keyMask });
    } finally {
      clearTimeout(timeout);
      release();
      logger.info('chat', {
        path: '/v1/chat',
        stream: true,
        model,
        tokens,
        ttftMs,
        queuedMs,
        durationMs: Date.now() - started,
        key: keyMask,
      });
    }
    return;
  }

  // ── Non-streaming branch ──────────────────────────────────────────────────
  try {
    const result = await chat(params);
    res.json(result);
    logger.info('chat', {
      path: '/v1/chat',
      model: result.model,
      tokens: result.usage.total_tokens,
      queuedMs,
      durationMs: Date.now() - started,
      key: keyMask,
    });
  } catch (e) {
    if (ctrl.signal.aborted) {
      res.status(503).json({
        error: 'model_timeout',
        message: 'The model took too long or the request was aborted.',
      });
    } else if (e instanceof OllamaError) {
      if (e.status === 404) {
        res.status(400).json({
          error: 'model_not_found',
          message: `Model "${model}" is not installed. Run: ollama pull ${model}`,
        });
      } else {
        res.status(503).json({ error: 'model_unavailable', message: e.message });
      }
    } else {
      res.status(500).json({ error: 'internal_error' });
    }
    logger.error('chat error', { msg: (e as Error).message, key: keyMask });
  } finally {
    clearTimeout(timeout);
    release();
  }
});
