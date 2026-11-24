// AI-3 (BODY) — TypeScript mirror of the Jarvis daemon protocol (JARVIS_BUILD.md §2.3).
// Envelope: {"type": "...", "data": {...}, "t": 1763673300.12}. Keep in sync with the Python
// side (auri-jarvis/auri_jarvis/{contracts,bus,orchestrator}.py, hud/server.py).

export type DaemonState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking' | 'acting';
export type WakeWord = 'hey_auri' | 'hey_jarvis';
export type VoiceName = 'daniel' | 'george' | 'piper';
export type Tier = 'guest' | 'user';
export type PrefKey = 'address' | 'wake_word' | 'voice' | 'welcome_routine';

export interface RoutineApp {
  app: string;
  monitor: 1 | 2 | 3;
  fullscreen: boolean;
}
export interface RoutineUrl {
  url: string;
  monitor: 1 | 2 | 3;
}
export interface WelcomeRoutine {
  music_url: string | null;
  apps: RoutineApp[];
  urls: RoutineUrl[];
}

export interface JarvisPrefs {
  address: string;
  wake_word: WakeWord;
  voice: VoiceName;
  welcome_routine: WelcomeRoutine | null;
  answered: PrefKey[];
  onboarded: boolean;
}

export const GUEST_PREFS: JarvisPrefs = {
  address: 'you',
  wake_word: 'hey_auri',
  voice: 'daniel',
  welcome_routine: null,
  answered: [],
  onboarded: false,
};

export interface Envelope<T extends string = string, D = Record<string, unknown>> {
  type: T;
  data: D;
  t: number;
}

// ── daemon → HUD ──────────────────────────────────────────────────────────────
export interface DaemonEvents {
  hello: { version: string };
  state: { state: DaemonState; since: number; prev?: DaemonState | null; follow_up?: boolean };
  level: { source: 'mic' | 'out'; rms: number };
  wake: { source: string; word: WakeWord | null; confidence: number };
  transcript: { raw: string; text: string; lang: string; engine: string; stt_ms: number; speech_ms?: number; confidence?: number };
  route: { path: 'fastpath' | 'llm' | 'trigger' | 'onboarding' | 'denied'; intent?: string | null };
  'reply.delta': { text: string };
  'reply.done': { text: string; model?: string; llm_first_ms?: number; tokens?: number };
  tool: { name: string; args?: Record<string, unknown>; status: 'ok' | 'error' | 'denied' | 'needs_confirm'; ms?: number; message?: string };
  timing: {
    turn: number;
    channel?: string;
    path?: string | null;
    wake_ack_ms: number | null;
    speech_ms: number | null;
    stt_ms: number | null;
    llm_first_ms: number | null;
    tts_first_ms: number | null;
    total_ms: number | null;
    turn_ms?: number | null;
  };
  identity: { tier: Tier; name: string | null; user_id?: string | null; prefs: JarvisPrefs; updated_at?: number | null };
  onboarding: { step: 1 | 2 | 3 | 4; question?: string; options?: unknown };
  'prefs.changed': { prefs: JarvisPrefs; updated_at: number; source?: string };
  options: { apps: { id: string; name: string }[]; monitors: { n: number; name: string; width: number; height: number; primary?: boolean }[] };
  'tts.credits': { used_month: number; budget: number; mode: string };
  proposal: { id: number | string; text: string };
  stats: { cpu: number; ram: number; ollama: string };
  mute: { on: boolean };
  // AI-3 addition to §2.3: background warm-up of the Mind (LLM) and the voice (TTS) — sticky
  warmup: { mind: WarmStatus; voice: WarmStatus; ms: number };
  error: { where: string; message: string };
}
export type WarmStatus = 'loading' | 'ready' | 'error';
export type DaemonEventType = keyof DaemonEvents;
export type DaemonMessage = { [K in DaemonEventType]: Envelope<K, DaemonEvents[K]> }[DaemonEventType];

// ── HUD → daemon ──────────────────────────────────────────────────────────────
export interface HudCommands {
  hello: Record<string, never>;
  ptt: { down: boolean };
  command: { text: string };
  stop: Record<string, never>;
  mute: { on: boolean };
  auth: { access_token: string };
  logout: Record<string, never>;
  'prefs.set': Partial<JarvisPrefs>;
  'voice.sample': { voice: VoiceName };
  'proposal.answer': { id: number | string; accept: boolean };
}
export type HudCommandType = keyof HudCommands;

export function envelope<K extends HudCommandType>(type: K, data: HudCommands[K]): string {
  return JSON.stringify({ type, data, t: Date.now() / 1000 });
}
