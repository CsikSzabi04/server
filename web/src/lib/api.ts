// Chat transport. Three modes, one interface:
//   - MOCK  (no VITE_API_URL): simulated streaming of canned replies.
//   - LIVE  (VITE_API_URL set): real fetch, supports SSE streaming OR plain JSON.
// The UI only ever sees a stream of text deltas, so it doesn't care which mode.
import { pickMockReply } from './mockResponses';

export type Role = 'system' | 'user' | 'assistant';

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface StreamCallbacks {
  onStart?: () => void;
  onDelta: (text: string) => void;
  onDone: (info: { usage?: ChatUsage; latencyMs: number }) => void;
  onError: (message: string) => void;
}

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
): Promise<void> {
  return getMode() === 'mock' ? mockStream(messages, cb, signal) : liveStream(messages, cb, signal);
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
async function liveStream(messages: ChatMessage[], cb: StreamCallbacks, signal?: AbortSignal) {
  const started = performance.now();
  cb.onStart?.();

  const headers: Record<string, string> = { 'content-type': 'application/json' };
  // Only attach a client-side key for the DIRECT (private) mode. The PROXY mode
  // adds the key server-side, so none is needed (and none should be exposed).
  if (ENV_KEY && !ENV_URL.startsWith('/')) headers.authorization = `Bearer ${ENV_KEY}`;

  let res: Response;
  try {
    res = await fetch(ENV_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({ messages, stream: true, temperature: 0.7, max_tokens: 1024 }),
      signal,
    });
  } catch (e) {
    if ((e as DOMException).name === 'AbortError') return;
    cb.onError(`>> UPLINK LOST — ${(e as Error).message}`);
    return;
  }

  const contentType = res.headers.get('content-type') ?? '';

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

    cb.onDone({ usage, latencyMs: Math.round(performance.now() - started) });
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
    // small delay only if not aborted
    try {
      await sleep(/^\s+$/.test(tok) ? 8 : 18, signal);
    } catch {
      return;
    }
  }
  cb.onDone({ usage: data?.usage, latencyMs: Math.round(performance.now() - started) });
}
