// core-client — the AuriGPT side of the local Auri Core (owner: AI-3, P1).
// Spec: ideas_for_brain/thinking/01-architektura/03-hol-fut-auri-core.md §4 (API), §7.4 (switch).
//
// The Core runs only on the user's own PC (127.0.0.1:8791). It is OFF by default: the switch is
// localStorage `auri.brain.core` = "1". When it is off or the Core is unreachable, callers keep the
// old in-browser brain (this module never throws for "not available" — it returns null / false).
//
// Auth: `Authorization: Bearer <core token>` (from `auri-core/data/core.token`; dev: VITE_AURI_CORE_TOKEN
// in web/.env.local, or pasted once into localStorage `auri.core.token`) + optional `X-Auri-User:
// <Supabase access token>` — signed in → own T1 too; without it the Core treats the caller as a guest.
// The refresh token is never sent.

import { supabase } from '../lib/supabase';

export const CORE_SWITCH_KEY = 'auri.brain.core';
export const CORE_TOKEN_KEY = 'auri.core.token';
const DEFAULT_URL = 'http://127.0.0.1:8791/core/v1';

export type CoreMode = 'chat' | 'code' | 'research';
export type CoreEventType = 'route' | 'step' | 'delta' | 'verify' | 'done' | 'error';
export interface CoreEvent {
  type: CoreEventType;
  data: Record<string, unknown>;
}
export interface CoreAskRequest {
  text: string;
  mode?: CoreMode;
  lang?: 'hu' | 'en';
  context?: string[];
  allow_web?: boolean;
  allow_cloud?: boolean;
}
export interface CoreSource {
  relation: string;
  ref_type: string;
  ref_id: string;
}
export interface CoreRecallItem {
  type: 'knowledge' | 'snippet';
  id: string;
  title: string;
  body: string;
  status: string;
  trust: number;
  score: number;
  tier: 'T0' | 'T1';
  sources: CoreSource[];
  lang?: string;
  code?: string;
}
export interface CoreHealth {
  ok: boolean;
  identity: boolean;
  ollama: { ok: boolean; loaded: string[] };
  lane: { busy: boolean; prio: string | null; queue: number; user_active: boolean };
}

function lsGet(key: string): string | null {
  try {
    return globalThis.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

/** The `auri.brain.core` switch (default off). */
export function isCoreEnabled(): boolean {
  return lsGet(CORE_SWITCH_KEY) === '1';
}

export function setCoreEnabled(on: boolean): void {
  try {
    if (on) globalThis.localStorage?.setItem(CORE_SWITCH_KEY, '1');
    else globalThis.localStorage?.removeItem(CORE_SWITCH_KEY);
  } catch {
    /* storage blocked: the switch simply stays off */
  }
}

function env(name: string): string | undefined {
  const v = (import.meta as { env?: Record<string, string | undefined> }).env?.[name];
  return v && v.trim() ? v.trim() : undefined;
}

export function coreUrl(): string {
  return (env('VITE_AURI_CORE_URL') ?? DEFAULT_URL).replace(/\/+$/, '');
}

function coreToken(): string | null {
  return env('VITE_AURI_CORE_TOKEN') ?? lsGet(CORE_TOKEN_KEY);
}

async function headers(json: boolean): Promise<Record<string, string> | null> {
  const token = coreToken();
  if (!token) return null;
  const h: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (json) h['Content-Type'] = 'application/json';
  try {
    const { data } = (await supabase?.auth.getSession()) ?? { data: { session: null } };
    const access = data.session?.access_token;
    if (access) h['X-Auri-User'] = access; // access token only — never the refresh token
  } catch {
    /* not signed in → guest */
  }
  return h;
}

async function call<T>(method: 'GET' | 'POST' | 'DELETE', path: string, body?: unknown, timeoutMs = 8000): Promise<T | null> {
  if (!isCoreEnabled()) return null;
  const h = await headers(body !== undefined);
  if (!h) return null;
  try {
    const r = await fetch(`${coreUrl()}${path}`, {
      method,
      headers: h,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null; // Core off / unreachable → caller falls back to the browser brain
  }
}

export async function coreHealth(): Promise<CoreHealth | null> {
  return call<CoreHealth>('GET', '/health', undefined, 2500);
}

/** True when the switch is on AND the Core answers. Cheap enough to call before each turn. */
export async function coreAvailable(): Promise<boolean> {
  return (await coreHealth())?.ok === true;
}

export async function coreRecall(query: string, k = 5, lang?: 'hu' | 'en'): Promise<CoreRecallItem[]> {
  return (await call<{ items: CoreRecallItem[] }>('POST', '/recall', { query, k, lang }))?.items ?? [];
}

export async function coreLearn(item: { title: string; body: string; kind?: 'qa' | 'fact' | 'snippet' | 'doc'; lang?: string; source?: string }) {
  return call<{ ok: boolean; id: string; tier: 'T1'; status: 'hypothesis' }>('POST', '/learn', item);
}

export async function coreFeedback(itemId: string, verdict: 'good' | 'bad' | 'fix', correction = '') {
  return call<{ ok: boolean; tier: 'T0' | 'T1'; correction_id: string | null }>('POST', '/feedback', { item_id: itemId, verdict, correction });
}

/** Sent at the start/end of a user turn so background work on the Core yields the model at once. */
export async function coreActivity(state: 'active' | 'idle' = 'active'): Promise<void> {
  await call('POST', '/activity', { source: 'web', state }, 1500);
}

/** One-off migration (01/03 §7.3): the signed-in user's old `brain_state` → own T1 as hypotheses. */
export async function coreImportBrainState(state: unknown) {
  return call<{ ok: boolean; added: number; skipped: number; dropped: number }>('POST', '/import/brain-state', { state }, 60000);
}

export async function coreDeleteAccount() {
  return call<{ ok: boolean; deleted: boolean }>('DELETE', '/account');
}

/** Parse an SSE byte stream into events (`event: <type>` + `data: <json>`, blank line ends one). */
export async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<CoreEvent> {
  const reader = body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let cut: number;
      while ((cut = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, cut);
        buf = buf.slice(cut + 2);
        let type = '';
        const data: string[] = [];
        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) type = line.slice(7).trim();
          else if (line.startsWith('data: ')) data.push(line.slice(6));
        }
        if (!type) continue;
        try {
          yield { type: type as CoreEventType, data: data.length ? JSON.parse(data.join('\n')) : {} };
        } catch {
          /* a broken event is skipped, the stream goes on */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Ask the Core; yields its events. Returns (yields nothing) when the Core is off/unreachable, so the
 * caller can fall back. Abort with `signal` — the Core then closes the model stream and frees the lane.
 */
export async function* coreAsk(req: CoreAskRequest, signal?: AbortSignal): AsyncGenerator<CoreEvent> {
  if (!isCoreEnabled()) return;
  const h = await headers(true);
  if (!h) return;
  let r: Response;
  try {
    r = await fetch(`${coreUrl()}/ask`, { method: 'POST', headers: h, body: JSON.stringify(req), signal });
  } catch {
    return;
  }
  if (!r.ok || !r.body) {
    yield { type: 'error', data: { kind: 'http', message: `a Core hibát adott (${r.status})` } };
    return;
  }
  yield* parseSSE(r.body);
}

/** Convenience: collect a whole answer. null → Core not available (use the browser brain). */
export async function coreAnswer(req: CoreAskRequest, signal?: AbortSignal): Promise<{ text: string; done?: CoreEvent; error?: CoreEvent } | null> {
  let text = '';
  let done: CoreEvent | undefined;
  let error: CoreEvent | undefined;
  let any = false;
  for await (const ev of coreAsk(req, signal)) {
    any = true;
    if (ev.type === 'delta') text += String(ev.data.text ?? '');
    else if (ev.type === 'done') done = ev;
    else if (ev.type === 'error') error = ev;
  }
  return any ? { text, done, error } : null;
}

// ── long tasks (P5): signed-in only; each user sees only their own ───────────────────────────
export type CoreTaskState = 'queued' | 'running' | 'paused' | 'interrupted' | 'done' | 'failed' | 'cancelled';
export interface CoreTask {
  id: string;
  state: CoreTaskState;
  goal: string;
  mode: 'project' | 'research';
  created_at: string;
  updated_at: string;
  attempts: number;
  last_step: string | null;
  outcome: string | null;
  events: number;
}

export async function coreTaskStart(text: string, mode: 'project' | 'research' = 'project', allowWeb = false) {
  return call<{ ok: boolean; id: string }>('POST', '/tasks', { text, mode, allow_web: allowWeb });
}

export async function coreTasks(): Promise<CoreTask[]> {
  return (await call<{ tasks: CoreTask[] }>('GET', '/tasks'))?.tasks ?? [];
}

export async function coreTaskControl(id: string, action: 'pause' | 'resume' | 'cancel') {
  return call<{ ok: boolean; task: CoreTask | null }>('POST', `/tasks/${encodeURIComponent(id)}/${action}`);
}

/** History from `start`, then live events until the task stops. Leaving does not stop the task. */
export async function* coreTaskEvents(id: string, start = 0, signal?: AbortSignal): AsyncGenerator<CoreEvent> {
  if (!isCoreEnabled()) return;
  const h = await headers(false);
  if (!h) return;
  let r: Response;
  try {
    r = await fetch(`${coreUrl()}/tasks/${encodeURIComponent(id)}/events?start=${start}`, { headers: h, signal });
  } catch {
    return;
  }
  if (!r.ok || !r.body) return;
  yield* parseSSE(r.body);
}
