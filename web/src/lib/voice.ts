// AuriGPT's spoken voice. Two free engines behind one interface:
//
//   • 'web'   — browser Web Speech API (window.speechSynthesis). Runs on the
//               visitor's device. Zero server cost. Voice quality is device-
//               dependent. Used when there is no backend (MOCK / GitHub Pages).
//   • 'piper' — local neural TTS on the server (POST /api/tts -> WAV), played
//               here via Web Audio. Consistent, nicer Hungarian voice. Used
//               automatically when a backend is configured.
//
// Engine choice: VITE_TTS_ENGINE = 'auto' (default) | 'web' | 'piper'.
// In 'auto'/'piper' we use Piper when a backend URL exists, else Web Speech.
// Any Piper failure (no /v1/tts, network error) falls back to Web Speech.
//
// Speaks sentence-by-sentence as the reply streams in. OFF by default; the
// user flips it with the VOICE toggle. Preference persisted in localStorage.
import { apiAuthHeader } from './authFetch';

const LS_KEY = 'auri.voice';

let enabled = readPref();
let buffer = '';

const ENV_TTS_ENGINE = (import.meta.env.VITE_TTS_ENGINE as string | undefined)?.trim().toLowerCase() || 'auto';
const ENV_KEY = (import.meta.env.VITE_API_KEY as string | undefined)?.trim() || '';

function readPref(): boolean {
  try {
    return localStorage.getItem(LS_KEY) === '1';
  } catch {
    return false;
  }
}

// ── shared helpers ───────────────────────────────────────────────────────────

function hasWebSpeech(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

function audioCtxCtor(): typeof AudioContext | undefined {
  if (typeof window === 'undefined') return undefined;
  return window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
}

// Derive the TTS endpoint from the chat endpoint: '/api/chat' -> '/api/tts',
// 'https://host/v1/chat' -> 'https://host/v1/tts'. Empty (MOCK) -> null.
function ttsUrl(): string | null {
  const chat = (import.meta.env.VITE_API_URL as string | undefined)?.trim() || '';
  if (!chat) return null;
  if (chat.startsWith('/')) return chat.replace(/chat\/?$/, 'tts');
  return chat.replace(/\/v1\/chat\/?$/, '/v1/tts');
}

function piperPossible(): boolean {
  return !!ttsUrl() && !!audioCtxCtor();
}

function activeEngine(): 'web' | 'piper' {
  if (ENV_TTS_ENGINE === 'web') return 'web';
  if (ENV_TTS_ENGINE === 'piper') return piperPossible() ? 'piper' : 'web';
  return piperPossible() ? 'piper' : 'web'; // auto
}

// Strip the most common markdown so neither engine reads out symbols.
function clean(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_#>~|]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// ── Web Speech engine ────────────────────────────────────────────────────────

let preferredVoice: SpeechSynthesisVoice | null = null;

function pickWebVoice(): void {
  if (!hasWebSpeech()) return;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return;
  preferredVoice =
    voices.find((v) => v.lang?.toLowerCase().startsWith('hu')) ??
    voices.find((v) => /hungar|magyar|szabolcs/i.test(v.name)) ??
    null;
}

if (hasWebSpeech()) {
  pickWebVoice();
  window.speechSynthesis.addEventListener('voiceschanged', pickWebVoice);
}

function webEnqueue(sentence: string): void {
  const text = clean(sentence);
  if (!text || !hasWebSpeech()) return;
  const u = new SpeechSynthesisUtterance(text);
  if (preferredVoice) u.voice = preferredVoice;
  u.lang = preferredVoice?.lang ?? 'hu-HU';
  u.rate = 1.02;
  u.pitch = 1.0;
  u.volume = 1.0;
  window.speechSynthesis.speak(u);
}

function webCancel(): void {
  if (!hasWebSpeech()) return;
  try {
    window.speechSynthesis.cancel();
  } catch {
    /* ignore */
  }
}

// ── Piper engine (server WAV played gaplessly via Web Audio) ─────────────────

let audioCtx: AudioContext | null = null;
let playCursor = 0;
const activeSources = new Set<AudioBufferSourceNode>();
const synthQueue: string[] = [];
let pumping = false;
let piperAbort: AbortController | null = null;

function getCtx(): AudioContext | null {
  const Ctor = audioCtxCtor();
  if (!Ctor) return null;
  audioCtx ??= new Ctor();
  return audioCtx;
}

async function pump(): Promise<void> {
  if (pumping) return;
  pumping = true;
  try {
    while (synthQueue.length) {
      const sentence = clean(synthQueue.shift() as string);
      if (!sentence) continue;
      const url = ttsUrl();
      const ctx = getCtx();
      if (!url || !ctx) continue;

      piperAbort = new AbortController();
      let wav: ArrayBuffer;
      try {
        const headers: Record<string, string> = { 'content-type': 'application/json' };
        // Direct (non-proxy) calls need the key; the proxy adds it server-side.
        if (ENV_KEY && !url.startsWith('/')) headers.authorization = `Bearer ${ENV_KEY}`;
        Object.assign(headers, await apiAuthHeader(url)); // same-origin proxy only
        const res = await fetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify({ text: sentence }),
          signal: piperAbort.signal,
        });
        if (!res.ok) {
          webEnqueue(sentence); // backend TTS down -> fall back for this chunk
          continue;
        }
        wav = await res.arrayBuffer();
      } catch {
        return; // aborted / network error -> stop the pump
      }

      let buf: AudioBuffer;
      try {
        buf = await ctx.decodeAudioData(wav.slice(0));
      } catch {
        continue; // undecodable -> skip
      }

      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      const start = Math.max(ctx.currentTime, playCursor);
      src.start(start);
      playCursor = start + buf.duration;
      activeSources.add(src);
      src.onended = () => activeSources.delete(src);
    }
  } finally {
    pumping = false;
  }
}

function piperEnqueue(sentence: string): void {
  synthQueue.push(sentence);
  void pump();
}

function piperCancel(): void {
  synthQueue.length = 0;
  piperAbort?.abort();
  piperAbort = null;
  for (const s of activeSources) {
    try {
      s.stop();
    } catch {
      /* already stopped */
    }
  }
  activeSources.clear();
  playCursor = audioCtx ? audioCtx.currentTime : 0;
}

// ── public API ───────────────────────────────────────────────────────────────

export function voiceSupported(): boolean {
  return hasWebSpeech() || !!audioCtxCtor();
}

export function isVoiceOn(): boolean {
  return enabled;
}

export function setVoiceOn(on: boolean): void {
  enabled = on;
  try {
    localStorage.setItem(LS_KEY, on ? '1' : '0');
  } catch {
    /* storage blocked — in-memory only */
  }
  if (on) {
    // This runs inside the toggle click (a user gesture), which unlocks audio
    // playback for the Piper engine.
    getCtx()?.resume().catch(() => {/* ignore */});
  } else {
    cancel();
  }
}

function enqueue(text: string): void {
  if (activeEngine() === 'piper') piperEnqueue(text);
  else webEnqueue(text);
}

const TERMINATORS = '.!?…\n';

/** Feed streaming text; speaks up to the last complete sentence, keeps the rest. */
export function feed(delta: string): void {
  if (!enabled || typeof window === 'undefined') return;
  buffer += delta;
  let lastIdx = -1;
  for (let i = buffer.length - 1; i >= 0; i--) {
    if (TERMINATORS.includes(buffer[i])) {
      lastIdx = i;
      break;
    }
  }
  if (lastIdx >= 0) {
    const ready = buffer.slice(0, lastIdx + 1);
    buffer = buffer.slice(lastIdx + 1);
    enqueue(ready);
  }
}

/** Speak whatever remains in the buffer (call when the stream completes). */
export function flush(): void {
  if (!enabled) return;
  const rest = buffer;
  buffer = '';
  if (rest.trim()) enqueue(rest);
}

/** Stop all speech and clear buffers (new turn / abort / mute). Cancels both engines. */
export function cancel(): void {
  buffer = '';
  webCancel();
  piperCancel();
}
