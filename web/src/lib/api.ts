// Chat transport. Three modes, one interface:
//   - MOCK  (no VITE_API_URL): simulated streaming of canned replies.
//   - LIVE  (VITE_API_URL set): real fetch, supports SSE streaming OR plain JSON.
// The UI only ever sees a stream of text deltas, so it doesn't care which mode.
import { pickMockReply } from './mockResponses';
import { getPrefs, getCustomModel } from './modelStore';
import { forcedModelId, forcedProvider } from './aiModels';
import { byoStream } from './byo';
import { apiAuthHeader } from './authFetch';

export type Role = 'system' | 'user' | 'assistant';

export interface ChatMessage {
  role: Role;
  content: string;
  /** Images on a user turn, as data:image/(png|jpeg|webp|gif);base64 URLs. Only vision-capable
   *  providers receive them; such requests are never cached (image bytes stay out of memory). */
  images?: string[];
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/** What answered a request — shown under replies (e.g. "groq · gpt-oss-120b · 2310 → 3980"). */
export interface DoneInfo {
  usage?: ChatUsage;
  latencyMs: number;
  /** 'ollama' | 'groq' | 'gemini' | 'byo' | 'mock' (from the X-Auri-Source header). */
  source?: string;
  /** The model id that answered (X-Auri-Model header, JSON body, or the forced pick). */
  model?: string;
  /** Replayed from the client cache — no new tokens were spent. */
  cached?: boolean;
}

export interface StreamCallbacks {
  onStart?: () => void;
  onDelta: (text: string) => void;
  onDone: (info: DoneInfo) => void;
  onError: (message: string) => void;
}

export interface StreamOpts {
  temperature?: number;
  maxTokens?: number;
  /** Reuse a cached reply for an identical request (default: true in live mode). */
  cache?: boolean;
}

// Small client-side cache: identical request -> instant replay (no round-trip).
const replyCache = new Map<string, { reply: string; usage?: ChatUsage; source?: string; model?: string }>();
const cacheKey = (messages: ChatMessage[], opts?: StreamOpts) =>
  JSON.stringify({ m: messages, t: opts?.temperature ?? 0.7, k: opts?.maxTokens ?? 1024 });

const ENV_URL = (import.meta.env.VITE_API_URL as string | undefined)?.trim() || '';
const ENV_KEY = (import.meta.env.VITE_API_KEY as string | undefined)?.trim() || '';

export function getMode(): 'mock' | 'live' {
  return ENV_URL ? 'live' : 'mock';
}

export function getEndpointLabel(): string {
  if (!ENV_URL) return 'MOCK';
  if (ENV_URL.startsWith('/')) return 'PROXY';
  return 'DIRECT';
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException('aborted', 'AbortError'));
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(t);
        reject(new DOMException('aborted', 'AbortError'));
      },
      { once: true },
    );
  });

export async function streamChat(
  messages: ChatMessage[],
  cb: StreamCallbacks,
  signal?: AbortSignal,
  opts?: StreamOpts,
): Promise<void> {
  // Apply the user's persisted model / mode choice (lib/modelStore).
  const prefs = getPrefs();
  if (prefs.mode === 'agent') {
    messages = [
      {
        role: 'system',
        content:
          'Operate in AGENT mode: be proactive and thorough. Break the task into clear steps, ' +
          'reason explicitly, and finish with concrete next actions.',
      },
      ...messages,
    ];
  }
  // BYO: call the user's OWN provider directly — the key never leaves the device.
  const custom = getCustomModel(prefs.selectedId);
  if (custom)
    return byoStream(
      custom,
      messages,
      { ...cb, onDone: (i) => cb.onDone({ ...i, source: 'byo', model: i.model ?? custom.model }) },
      signal,
    );

  if (getMode() === 'mock')
    return mockStream(messages, { ...cb, onDone: (i) => cb.onDone({ ...i, source: 'mock' }) }, signal);

  const useCache = opts?.cache !== false && !messages.some((m) => m.images?.length);
  const key = useCache ? cacheKey(messages, opts) : '';

  // Cache hit -> replay instantly, word by word so the UI still animates.
  if (useCache) {
    const hit = replyCache.get(key);
    if (hit) {
      const started = performance.now();
      cb.onStart?.();
      for (const tok of hit.reply.match(/\s+|\S+/g) ?? [hit.reply]) {
        if (signal?.aborted) return;
        cb.onDelta(tok);
      }
      cb.onDone({
        usage: hit.usage,
        source: hit.source,
        model: hit.model,
        cached: true,
        latencyMs: Math.round(performance.now() - started),
      });
      return;
    }
  }

  // Wrap callbacks to capture the full reply for the cache on success.
  let full = '';
  const wrapped: StreamCallbacks = {
    onStart: cb.onStart,
    onDelta: (t) => {
      full += t;
      cb.onDelta(t);
    },
    onDone: (info) => {
      if (useCache && full.trim()) {
        replyCache.set(key, { reply: full, usage: info.usage, source: info.source, model: info.model });
        if (replyCache.size > 24) {
          const oldest = replyCache.keys().next().value;
          if (oldest) replyCache.delete(oldest);
        }
      }
      cb.onDone(info);
    },
    onError: cb.onError,
  };
  return liveStream(messages, wrapped, signal, opts);
}

// ── MOCK ─────────────────────────────────────────────────────────────────────
async function mockStream(messages: ChatMessage[], cb: StreamCallbacks, signal?: AbortSignal) {
  const started = performance.now();
  cb.onStart?.();
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')?.content ?? '';
  const reply = pickMockReply(lastUser);

  try {
    // simulate "thinking" latency
    await sleep(450 + Math.random() * 500, signal);

    // emit word-by-word so the typewriter + per-word entrance animation shows
    const tokens = reply.match(/\s+|\S+/g) ?? [reply];
    for (const tok of tokens) {
      cb.onDelta(tok);
      await sleep(/^\s+$/.test(tok) ? 12 : 28 + Math.random() * 34, signal);
    }

    const completion = Math.round(reply.length / 4);
    cb.onDone({
      usage: { prompt_tokens: 16, completion_tokens: completion, total_tokens: 16 + completion },
      latencyMs: Math.round(performance.now() - started),
    });
  } catch (e) {
    if ((e as DOMException).name === 'AbortError') return;
    cb.onError((e as Error).message);
  }
}

// ── LIVE ─────────────────────────────────────────────────────────────────────
async function liveStream(
  messages: ChatMessage[],
  cb: StreamCallbacks,
  signal?: AbortSignal,
  opts?: StreamOpts,
) {
  const started = performance.now();
  cb.onStart?.();

  const headers: Record<string, string> = { 'content-type': 'application/json' };
  // Only attach a client-side key for the DIRECT (private) mode. The PROXY mode
  // adds the key server-side, so none is needed (and none should be exposed).
  if (ENV_KEY && !ENV_URL.startsWith('/')) headers.authorization = `Bearer ${ENV_KEY}`;
  // PROXY mode: identify the signed-in user to our own /api (same-origin only).
  Object.assign(headers, await apiAuthHeader(ENV_URL));

  let res: Response;
  try {
    res = await fetch(ENV_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        messages,
        // Ollama selections force a model; Groq/Gemini selections force that
        // provider; Auto leaves both unset so the server chain decides.
        model: forcedModelId(getPrefs().selectedId),
        provider: forcedProvider(getPrefs().selectedId),
        stream: true,
        temperature: opts?.temperature ?? 0.7,
        max_tokens: opts?.maxTokens ?? 1024,
      }),
      signal,
    });
  } catch (e) {
    if ((e as DOMException).name === 'AbortError') return;
    cb.onError(`>> UPLINK LOST — ${(e as Error).message}`);
    return;
  }

  const contentType = res.headers.get('content-type') ?? '';
  // Who answered: the proxy tags the provider; the model comes from a header (streams),
  // the JSON body, or — for an older local server — the Ollama model we forced.
  const source = res.headers.get('x-auri-source') ?? undefined;
  const headerModel = res.headers.get('x-auri-model') ?? undefined;
  const forced = forcedModelId(getPrefs().selectedId);

  // Non-OK and JSON error -> surface message
  if (!res.ok && !contentType.includes('text/event-stream')) {
    const data = await res.json().catch(() => ({}) as any);
    cb.onError(`>> ERROR ${res.status} — ${data?.message ?? data?.error ?? 'backend error'}`);
    return;
  }

  // ── SSE streaming branch ──
  if (contentType.includes('text/event-stream') && res.body) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let usage: ChatUsage | undefined;

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) >= 0) {
          const rawEvent = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);

          for (const line of rawEvent.split('\n')) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            const data = trimmed.slice(5).trim();
            if (data === '[DONE]') continue;
            try {
              const obj = JSON.parse(data);
              if (typeof obj.delta === 'string') cb.onDelta(obj.delta);
              if (obj.usage) usage = obj.usage;
              if (obj.error) cb.onError(`>> ${obj.error}: ${obj.message ?? ''}`);
            } catch {
              /* ignore partial */
            }
          }
        }
      }
    } catch (e) {
      if ((e as DOMException).name === 'AbortError') return;
      cb.onError(`>> STREAM INTERRUPTED — ${(e as Error).message}`);
      return;
    }

    cb.onDone({
      usage,
      source,
      model: headerModel ?? (source === 'ollama' ? forced : undefined),
      latencyMs: Math.round(performance.now() - started),
    });
    return;
  }

  // ── Plain JSON branch ({ reply, usage }) -> chunk it for the live effect ──
  const data = await res.json().catch(() => ({}) as any);
  const reply: string = data?.reply ?? '';
  if (!reply) {
    cb.onError('>> EMPTY RESPONSE');
    return;
  }
  const tokens = reply.match(/\s+|\S+/g) ?? [reply];
  for (const tok of tokens) {
    cb.onDelta(tok);
    // small delay only if not aborted (kept minimal so the reply lands fast)
    try {
      await sleep(/^\s+$/.test(tok) ? 2 : 6, signal);
    } catch {
      return;
    }
  }
  cb.onDone({
    usage: data?.usage,
    source,
    model: (typeof data?.model === 'string' ? data.model : undefined) ?? headerModel ?? (source === 'ollama' ? forced : undefined),
    latencyMs: Math.round(performance.now() - started),
  });
}
