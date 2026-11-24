// AI-3 (BODY) — WebSocket link to the local Jarvis daemon (ws://127.0.0.1:8790/events).
//
// Token: the daemon injects <meta name="jarvis-token"> into the page it serves. In Vite dev
// (localhost:5173) pass it once as ?token=… or #jarvis&token=… — it is then kept in
// localStorage and stripped from the URL. Reconnects with backoff (0.5 s → 5 s).
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import type { UIMessage } from '../types';
import {
  type DaemonEvents,
  type DaemonMessage,
  type DaemonState,
  type HudCommandType,
  type HudCommands,
  type JarvisPrefs,
  GUEST_PREFS,
  envelope,
} from './protocol';

const TOKEN_KEY = 'auri.jarvis.hudToken';
const DAEMON_PORT = '8790';

export type LinkStatus = 'connecting' | 'open' | 'closed' | 'no-token';

export interface ToolEntry {
  name: string;
  status: DaemonEvents['tool']['status'];
  ms?: number;
  message?: string;
  t: number;
}

export interface JarvisModel {
  state: DaemonState;
  since: number;
  followUp: boolean;
  mic: number;
  out: number;
  transcript: DaemonEvents['transcript'] | null;
  reply: string;
  replyPending: boolean;
  replyModel: string | null;
  route: DaemonEvents['route'] | null;
  tools: ToolEntry[];
  timings: DaemonEvents['timing'][];
  identity: { tier: 'guest' | 'user'; name: string | null; userId: string | null; prefs: JarvisPrefs };
  onboardingStep: number | null;
  options: DaemonEvents['options'];
  credits: DaemonEvents['tts.credits'] | null;
  proposals: DaemonEvents['proposal'][];
  stats: DaemonEvents['stats'] | null;
  muted: boolean;
  warmup: DaemonEvents['warmup'] | null;
  errors: (DaemonEvents['error'] & { t: number })[];
  prefsChanged: (DaemonEvents['prefs.changed'] & { seq: number }) | null;
  version: string | null;
  /** LLM output tokens generated since this HUD connected (sum of reply.done.tokens). */
  tokens: number;
  /** The live conversation (voice transcripts + typed commands + streamed replies). */
  chat: UIMessage[];
}

export type LocalAction =
  | { type: 'local.clearProposal'; id: number | string }
  | { type: 'local.userText'; text: string }
  | { type: 'local.newChat' }
  | { type: 'local.loadChat'; messages: UIMessage[] };

let seq = 0;
const nextId = () => `jv-${Date.now().toString(36)}-${(seq++).toString(36)}`;
const CHAT_CAP = 80;

export const INITIAL_MODEL: JarvisModel = {
  state: 'idle',
  since: 0,
  followUp: false,
  mic: 0,
  out: 0,
  transcript: null,
  reply: '',
  replyPending: false,
  replyModel: null,
  route: null,
  tools: [],
  timings: [],
  identity: { tier: 'guest', name: null, userId: null, prefs: GUEST_PREFS },
  onboardingStep: null,
  options: { apps: [], monitors: [] },
  credits: null,
  proposals: [],
  stats: null,
  muted: false,
  warmup: null,
  errors: [],
  prefsChanged: null,
  version: null,
  tokens: 0,
  chat: [],
};

const cap = <T,>(arr: T[], n: number) => (arr.length > n ? arr.slice(arr.length - n) : arr);

function pushUser(chat: UIMessage[], text: string): UIMessage[] {
  const t = text.trim();
  if (!t) return chat;
  return cap([...chat, { id: nextId(), role: 'user', content: t }], CHAT_CAP);
}

function appendAssistant(chat: UIMessage[], delta: string): UIMessage[] {
  const last = chat[chat.length - 1];
  if (last && last.role === 'assistant' && last.streaming) {
    return [...chat.slice(0, -1), { ...last, content: last.content + delta }];
  }
  return cap([...chat, { id: nextId(), role: 'assistant', content: delta.trimStart(), streaming: true }], CHAT_CAP);
}

function finishAssistant(chat: UIMessage[], text: string): UIMessage[] {
  const last = chat[chat.length - 1];
  if (last && last.role === 'assistant' && last.streaming) {
    return [...chat.slice(0, -1), { ...last, content: text || last.content, streaming: false }];
  }
  return text.trim() ? cap([...chat, { id: nextId(), role: 'assistant', content: text.trim() }], CHAT_CAP) : chat;
}

export function reduce(m: JarvisModel, msg: DaemonMessage | LocalAction): JarvisModel {
  switch (msg.type) {
    case 'local.clearProposal':
      return { ...m, proposals: m.proposals.filter((p) => p.id !== msg.id) };
    case 'local.userText':
      return { ...m, chat: pushUser(m.chat, msg.text) };
    case 'local.newChat':
      return { ...m, chat: [], reply: '', transcript: null, route: null };
    case 'local.loadChat':
      return { ...m, chat: cap(msg.messages, CHAT_CAP) };
    case 'hello':
      return { ...m, version: msg.data.version };
    case 'state': {
      const s = msg.data.state;
      const newTurn = s === 'thinking' && m.state !== 'acting' && m.state !== 'speaking';
      return {
        ...m,
        state: s,
        since: msg.data.since,
        followUp: !!msg.data.follow_up,
        replyPending: newTurn ? true : m.replyPending,
        onboardingStep: m.onboardingStep,
        mic: s === 'listening' ? m.mic : 0,
        out: s === 'speaking' ? m.out : 0,
      };
    }
    case 'level':
      return msg.data.source === 'out' ? { ...m, out: msg.data.rms } : { ...m, mic: msg.data.rms };
    case 'transcript':
      return { ...m, transcript: msg.data, replyPending: true, chat: pushUser(m.chat, msg.data.text) };
    case 'route':
      return { ...m, route: msg.data };
    case 'reply.delta':
      return {
        ...(m.replyPending
          ? { ...m, reply: msg.data.text.trimStart(), replyPending: false }
          : { ...m, reply: m.reply + msg.data.text }),
        chat: appendAssistant(m.chat, msg.data.text),
      };
    case 'reply.done':
      return {
        ...m,
        reply: msg.data.text || m.reply,
        replyPending: false,
        replyModel: msg.data.model ?? null,
        tokens: m.tokens + Math.max(0, Number(msg.data.tokens) || 0),
        chat: finishAssistant(m.chat, msg.data.text),
      };
    case 'tool':
      return { ...m, tools: cap([...m.tools, { ...msg.data, t: msg.t }], 12) };
    case 'timing':
      return { ...m, timings: cap([...m.timings, msg.data], 8) };
    case 'identity': {
      const prefs = { ...GUEST_PREFS, ...(msg.data.prefs ?? {}) };
      const tier = msg.data.tier;
      return {
        ...m,
        identity: { tier, name: msg.data.name, userId: msg.data.user_id ?? null, prefs },
        onboardingStep: tier === 'guest' || prefs.onboarded ? null : m.onboardingStep,
        proposals: tier === 'guest' ? [] : m.proposals,
      };
    }
    case 'onboarding':
      return { ...m, onboardingStep: msg.data.step };
    case 'prefs.changed':
      return {
        ...m,
        identity: { ...m.identity, prefs: { ...GUEST_PREFS, ...msg.data.prefs } },
        prefsChanged: { ...msg.data, seq: (m.prefsChanged?.seq ?? 0) + 1 },
      };
    case 'options':
      return { ...m, options: msg.data };
    case 'tts.credits':
      return { ...m, credits: msg.data };
    case 'proposal':
      return m.proposals.some((p) => p.id === msg.data.id) ? m : { ...m, proposals: cap([...m.proposals, msg.data], 5) };
    case 'stats':
      return { ...m, stats: msg.data };
    case 'mute':
      return { ...m, muted: msg.data.on };
    case 'warmup':
      return { ...m, warmup: msg.data };
    case 'error':
      return { ...m, errors: cap([...m.errors, { ...msg.data, t: msg.t }], 4) };
    default:
      return m;
  }
}

function readToken(): string | null {
  const meta = document.querySelector('meta[name="jarvis-token"]')?.getAttribute('content');
  if (meta) return meta;
  const search = new URLSearchParams(window.location.search);
  const hashQuery = window.location.hash.replace(/^#[^&?]*[&?]?/, '');
  const fromUrl = search.get('token') || new URLSearchParams(hashQuery).get('token');
  if (fromUrl) {
    try {
      localStorage.setItem(TOKEN_KEY, fromUrl);
    } catch {
      /* storage blocked — keep it in memory for this tab */
    }
    // strip the token from the address bar / history
    search.delete('token');
    const qs = search.toString();
    const hash = window.location.hash.split(/[&?]/)[0];
    window.history.replaceState(null, '', window.location.pathname + (qs ? `?${qs}` : '') + hash);
    return fromUrl;
  }
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function daemonHost(): string {
  const env = (import.meta.env?.VITE_JARVIS_HOST as string | undefined)?.trim();
  // served by a daemon (token injected, any port) → talk to that same daemon
  if (document.querySelector('meta[name="jarvis-token"]') || window.location.port === DAEMON_PORT) return window.location.host;
  return env || `127.0.0.1:${DAEMON_PORT}`;
}

export interface JarvisLink {
  model: JarvisModel;
  status: LinkStatus;
  send: <K extends HudCommandType>(type: K, data: HudCommands[K]) => boolean;
  clearProposal: (id: number | string) => void;
  setToken: (token: string) => void;
  /** Local-only changes of the model (typed message echo, new chat, loading history). */
  local: (action: LocalAction) => void;
}

export function useJarvisSocket(): JarvisLink {
  const [model, dispatch] = useReducer(reduce, INITIAL_MODEL);
  const [status, setStatus] = useState<LinkStatus>('connecting');
  const [token, setTokenState] = useState<string | null>(() => readToken());
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus('no-token');
      return;
    }
    let stopped = false;
    let retry = 500;
    let timer: number | undefined;

    const open = () => {
      if (stopped) return;
      setStatus('connecting');
      const ws = new WebSocket(`ws://${daemonHost()}/events?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;
      ws.onopen = () => {
        retry = 500;
        setStatus('open');
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(String(e.data)) as DaemonMessage;
          if (msg && typeof msg.type === 'string') dispatch(msg);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        setStatus('closed');
        if (!stopped) {
          timer = window.setTimeout(open, retry);
          retry = Math.min(retry * 2, 5000);
        }
      };
      ws.onerror = () => ws.close();
    };
    open();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [token]);

  const send = useCallback(<K extends HudCommandType>(type: K, data: HudCommands[K]): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(envelope(type, data));
    return true;
  }, []);

  const clearProposal = useCallback((id: number | string) => dispatch({ type: 'local.clearProposal', id }), []);

  const setToken = useCallback((t: string) => {
    const v = t.trim();
    if (!v) return;
    try {
      localStorage.setItem(TOKEN_KEY, v);
    } catch {
      /* ignore */
    }
    setTokenState(v);
  }, []);

  const local = useCallback((action: LocalAction) => dispatch(action), []);

  return { model, status, send, clearProposal, setToken, local };
}
