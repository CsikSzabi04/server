// Thin Ollama client. We talk to Ollama's native /api/chat (NDJSON streaming),
// /api/tags, and normalize everything into our own response shape so the public
// API surface stays stable even if we swap the backend later.
import { config } from './config';

export interface ChatMessage {
  role: string; // 'system' | 'user' | 'assistant'
  content: string;
  /** User turns only: raw base64 image payloads (Ollama's format, no data: prefix). */
  images?: string[];
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatParams {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  /** Override num_ctx (the vision model shares the Jarvis daemon's 8192 → no reload). */
  numCtx?: number;
  /** false = no hidden "thinking" tokens (gemma4 would otherwise spend the budget there). */
  think?: boolean;
  signal?: AbortSignal;
}

export interface ChatResult {
  reply: string;
  model: string;
  usage: ChatUsage;
  finish_reason: string;
}

export interface StreamChunk {
  delta?: string;
  done: boolean;
  usage?: ChatUsage;
  finish_reason?: string;
}

export class OllamaError extends Error {
  status: number;
  constructor(message: string, status = 503) {
    super(message);
    this.name = 'OllamaError';
    this.status = status;
  }
}

function buildBody(p: ChatParams, stream: boolean) {
  // Per-request values override config defaults; everything else comes from
  // the tuned defaults so output quality + speed stay consistent.
  const options: Record<string, unknown> = {
    temperature: typeof p.temperature === 'number' ? p.temperature : config.temperature,
    top_p: config.topP,
    top_k: config.topK,
    repeat_penalty: config.repeatPenalty,
    num_ctx: p.numCtx ?? config.ollamaNumCtx,
    num_predict: typeof p.maxTokens === 'number' ? p.maxTokens : config.ollamaNumPredict,
  };
  if (config.ollamaNumThread > 0) options.num_thread = config.ollamaNumThread;
  if (config.ollamaNumBatch > 0) options.num_batch = config.ollamaNumBatch;
  return {
    model: p.model || config.ollamaModel,
    messages: p.messages,
    stream,
    keep_alive: config.ollamaKeepAlive,
    ...(p.think === undefined ? {} : { think: p.think }),
    options,
  };
}

function usageFrom(promptTokens: number, completionTokens: number): ChatUsage {
  return {
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total_tokens: promptTokens + completionTokens,
  };
}

async function postChat(p: ChatParams, stream: boolean): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${config.ollamaUrl}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(buildBody(p, stream)),
      signal: p.signal,
    });
  } catch (e) {
    // Connection refused etc. -> Ollama not running / unreachable.
    throw new OllamaError(`cannot reach Ollama at ${config.ollamaUrl}: ${(e as Error).message}`, 503);
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    // 404 from Ollama usually means the model is not pulled.
    const status = res.status === 404 ? 404 : 502;
    throw new OllamaError(`Ollama responded ${res.status}: ${text.slice(0, 200)}`, status);
  }
  return res;
}

/** Non-streaming chat completion. */
export async function chat(p: ChatParams): Promise<ChatResult> {
  const res = await postChat(p, false);
  const data = (await res.json()) as Record<string, any>;
  const promptTokens = Number(data.prompt_eval_count ?? 0);
  const completionTokens = Number(data.eval_count ?? 0);
  return {
    reply: data.message?.content ?? '',
    model: data.model ?? (p.model || config.ollamaModel),
    usage: usageFrom(promptTokens, completionTokens),
    finish_reason: data.done_reason ?? 'stop',
  };
}

/**
 * Streaming chat completion. Yields incremental delta chunks, then a final
 * chunk with done=true carrying usage + finish_reason.
 * Ollama streams newline-delimited JSON objects (NDJSON).
 */
export async function* chatStream(p: ChatParams): AsyncGenerator<StreamChunk> {
  const res = await postChat(p, true);
  if (!res.body) throw new OllamaError('Ollama returned no stream body', 502);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let promptTokens = 0;
  let completionTokens = 0;
  let finishReason = 'stop';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let nl: number;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;

        let obj: Record<string, any>;
        try {
          obj = JSON.parse(line);
        } catch {
          continue; // ignore partial / malformed lines
        }

        const content = obj.message?.content;
        if (content) yield { delta: content, done: false };

        if (obj.prompt_eval_count != null) promptTokens = Number(obj.prompt_eval_count);
        if (obj.eval_count != null) completionTokens = Number(obj.eval_count);
        if (obj.done_reason) finishReason = obj.done_reason;
      }
    }
  } finally {
    // Make sure the underlying connection is released if the consumer stops early.
    try {
      await reader.cancel();
    } catch {
      /* noop */
    }
  }

  yield {
    done: true,
    usage: usageFrom(promptTokens, completionTokens),
    finish_reason: finishReason,
  };
}

/** Proxy Ollama's installed-models list (/api/tags). */
export async function listModels(signal?: AbortSignal): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(`${config.ollamaUrl}/api/tags`, { signal });
  } catch (e) {
    throw new OllamaError(`cannot reach Ollama: ${(e as Error).message}`, 503);
  }
  if (!res.ok) throw new OllamaError(`Ollama responded ${res.status}`, 502);
  return res.json();
}

/** Quick liveness probe used by /health. Never throws. */
export async function ping(timeoutMs = 3000): Promise<boolean> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${config.ollamaUrl}/api/tags`, { signal: ctrl.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Preload a model into memory (and keep it there via keep_alive) so the first
 * real request doesn't pay the cold-start load cost. Never throws.
 */
export async function warmup(model: string = config.ollamaModel): Promise<boolean> {
  try {
    const res = await fetch(`${config.ollamaUrl}/api/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'ok' }],
        stream: false,
        keep_alive: config.ollamaKeepAlive,
        options: { num_predict: 1, num_ctx: config.ollamaNumCtx },
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}
