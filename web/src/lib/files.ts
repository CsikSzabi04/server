// File ingestion for the BRAIN. Reads text documents (.txt/.md/.json/.csv/...),
// splits them into retrievable chunks, and (best-effort) asks the model for a
// short summary. The chunks are stored as 'doc' memories so the relevant parts
// get injected into the system prompt — refining future answers.
import { apiAuthHeader } from './authFetch';

export const ACCEPTED = '.txt,.md,.markdown,.json,.csv,.log,.text';
const TEXT_EXT = /\.(txt|md|markdown|json|csv|log|text)$/i;
const MAX_BYTES = 1_000_000; // 1 MB cap

/** Read a text-like file to a string, or throw a friendly (Hungarian) error. */
export async function readDocument(file: File): Promise<string> {
  if (file.size > MAX_BYTES) {
    throw new Error(`File too large (max ${Math.round(MAX_BYTES / 1000)} kB).`);
  }
  if (!TEXT_EXT.test(file.name) && !file.type.startsWith('text/')) {
    throw new Error('Only text files are supported (.txt, .md, .json, .csv, .log).');
  }
  return (await file.text()).trim();
}

/** Split text into ~size-char chunks on sentence boundaries (capped count). */
export function chunkText(text: string, size = 480, max = 24): string[] {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const parts = clean.split(/(?<=[.!?…])\s+/);
  const chunks: string[] = [];
  let buf = '';
  for (const p of parts) {
    if (buf && (buf + ' ' + p).length > size) {
      chunks.push(buf.trim());
      buf = p;
    } else {
      buf = buf ? `${buf} ${p}` : p;
    }
    if (chunks.length >= max) break;
  }
  if (buf && chunks.length < max) chunks.push(buf.trim());
  return chunks.slice(0, max);
}

function chatUrl(): string | null {
  return (import.meta.env.VITE_API_URL as string | undefined)?.trim() || null;
}

/** Best-effort: let the model summarise the document. Returns null if no backend. */
export async function summarizeWithModel(name: string, text: string): Promise<string | null> {
  const url = chatUrl();
  if (!url) return null;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...(await apiAuthHeader(url)) },
      body: JSON.stringify({
        messages: [
          {
            role: 'user',
            content: `Summarize the key points of the document "${name}" in 2-3 sentences:\n\n${text.slice(0, 4000)}`,
          },
        ],
        stream: false,
        max_tokens: 220,
      }),
      signal: AbortSignal.timeout(40_000),
    });
    if (!res.ok) return null;
    if ((res.headers.get('content-type') ?? '').includes('text/event-stream')) return null;
    const j = (await res.json()) as { reply?: string };
    return j.reply?.trim() || null;
  } catch {
    return null;
  }
}
