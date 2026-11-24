// BYO (bring-your-own-key) direct provider calls. These run in the browser and
// talk DIRECTLY to the provider the user configured — the key is read from the
// user's own localStorage and is never sent to our server. Two shapes:
//   - 'openai'  : OpenAI-compatible /chat/completions (OpenAI, Groq, OpenRouter, …)
//   - 'gemini'  : Google Generative Language API (API key in the URL)
// Note: some providers don't send browser CORS headers; Gemini does, OpenAI does
// with a project key. If a provider blocks CORS the call surfaces a clear error.
import type { ChatMessage, StreamCallbacks } from './api';
import type { CustomModel } from './modelStore';
import { parseDataUrl } from './images';

function abortableDelay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
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
}

// Emit a full reply word-by-word so the live typewriter animation still plays.
async function emitReply(
  reply: string,
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number },
  cb: StreamCallbacks,
  started: number,
  signal?: AbortSignal,
) {
  for (const tok of reply.match(/\s+|\S+/g) ?? [reply]) {
    cb.onDelta(tok);
    try {
      await abortableDelay(/^\s+$/.test(tok) ? 6 : 14, signal);
    } catch {
      return;
    }
  }
  cb.onDone({ usage, latencyMs: Math.round(performance.now() - started) });
}

/** OpenAI chat format; a user turn with images becomes text + image_url content parts. */
function toOpenAiMessages(messages: ChatMessage[]): unknown[] {
  return messages.map((m) =>
    m.images?.length
      ? {
          role: m.role,
          content: [
            { type: 'text', text: m.content },
            ...m.images.filter((u) => parseDataUrl(u)).map((url) => ({ type: 'image_url', image_url: { url } })),
          ],
        }
      : { role: m.role, content: m.content },
  );
}

export async function byoStream(
  custom: CustomModel,
  messages: ChatMessage[],
  cb: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const started = performance.now();
  cb.onStart?.();
  try {
    if (custom.provider === 'gemini') {
      const sys = messages.filter((m) => m.role === 'system').map((m) => m.content).join('\n');
      const contents = messages
        .filter((m) => m.role !== 'system')
        .map((m) => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [
            { text: m.content },
            ...(m.images ?? []).flatMap((u) => {
              const img = parseDataUrl(u);
              return img ? [{ inlineData: { mimeType: img.mime, data: img.data } }] : [];
            }),
          ],
        }));
      const r = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(custom.model)}:generateContent?key=${encodeURIComponent(custom.apiKey)}`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            systemInstruction: sys ? { parts: [{ text: sys }] } : undefined,
            contents,
            generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
          }),
          signal,
        },
      );
      if (!r.ok) {
        cb.onError(`>> ${custom.label}: HTTP ${r.status}`);
        return;
      }
      const j = (await r.json()) as any;
      const reply = ((j.candidates?.[0]?.content?.parts ?? []) as any[])
        .map((p) => p.text ?? '')
        .join('')
        .trim();
      if (!reply) {
        cb.onError('>> EMPTY RESPONSE');
        return;
      }
      const um = j.usageMetadata ?? {};
      await emitReply(
        reply,
        {
          prompt_tokens: um.promptTokenCount ?? 0,
          completion_tokens: um.candidatesTokenCount ?? 0,
          total_tokens: um.totalTokenCount ?? 0,
        },
        cb,
        started,
        signal,
      );
      return;
    }

    // OpenAI-compatible
    const base = (custom.baseUrl || 'https://api.openai.com/v1').replace(/\/+$/, '');
    const r = await fetch(`${base}/chat/completions`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${custom.apiKey}` },
      body: JSON.stringify({ model: custom.model, messages: toOpenAiMessages(messages), temperature: 0.7, max_tokens: 1024 }),
      signal,
    });
    if (!r.ok) {
      const t = await r.text().catch(() => '');
      cb.onError(`>> ${custom.label}: HTTP ${r.status} ${t.slice(0, 140)}`);
      return;
    }
    const j = (await r.json()) as any;
    const reply: string = j.choices?.[0]?.message?.content ?? '';
    if (!reply) {
      cb.onError('>> EMPTY RESPONSE');
      return;
    }
    const u = j.usage ?? {};
    await emitReply(
      reply,
      {
        prompt_tokens: u.prompt_tokens ?? 0,
        completion_tokens: u.completion_tokens ?? 0,
        total_tokens: u.total_tokens ?? 0,
      },
      cb,
      started,
      signal,
    );
  } catch (e) {
    if ((e as DOMException).name === 'AbortError') return;
    cb.onError(`>> ${custom.label} ERROR — ${(e as Error).message}`);
  }
}
