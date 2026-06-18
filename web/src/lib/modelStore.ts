// Persisted model selection + chat mode + the user's OWN (BYO) API providers.
//
// Everything lives in localStorage on the user's device → "profile-following"
// for this browser. BYO API keys NEVER leave the device except to call the
// user's own chosen provider directly (see lib/byo.ts). They are never sent to
// our server/proxy.

export type ChatMode = 'agent' | 'chat';
export type ByoProvider = 'openai' | 'gemini';

export interface CustomModel {
  id: string; // 'byo_xxx'
  label: string;
  provider: ByoProvider; // 'openai' = OpenAI-compatible (OpenAI, Groq, OpenRouter, …)
  baseUrl?: string; // OpenAI-compatible base, default https://api.openai.com/v1
  apiKey: string;
  model: string; // e.g. gpt-4o-mini / llama-3.3-70b-versatile / gemini-2.0-flash
}

interface PrefsState {
  selectedId: string; // built-in id ('auto', 'gemma2:2b', …) or a custom id
  mode: ChatMode;
  custom: CustomModel[];
}

const LS_KEY = 'auri.modelPrefs';
const DEFAULT: PrefsState = { selectedId: 'auto', mode: 'chat', custom: [] };

function load(): PrefsState {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return { ...DEFAULT };
    const p = JSON.parse(raw) as Partial<PrefsState>;
    return {
      selectedId: p.selectedId ?? 'auto',
      mode: p.mode === 'agent' ? 'agent' : 'chat',
      custom: Array.isArray(p.custom) ? p.custom : [],
    };
  } catch {
    return { ...DEFAULT };
  }
}

let state = load();
const listeners = new Set<() => void>();

function commit() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(state));
  } catch {
    /* storage blocked */
  }
  for (const fn of listeners) fn();
}

export function subscribePrefs(fn: () => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export const getPrefs = (): PrefsState => state;

export function setSelectedModel(id: string): void {
  state = { ...state, selectedId: id };
  commit();
}

export function setMode(mode: ChatMode): void {
  state = { ...state, mode };
  commit();
}

export function addCustomModel(m: Omit<CustomModel, 'id'>): CustomModel {
  const cm: CustomModel = { ...m, id: 'byo_' + Math.random().toString(36).slice(2, 9) };
  state = { ...state, custom: [...state.custom, cm], selectedId: cm.id };
  commit();
  return cm;
}

export function removeCustomModel(id: string): void {
  state = {
    ...state,
    custom: state.custom.filter((c) => c.id !== id),
    selectedId: state.selectedId === id ? 'auto' : state.selectedId,
  };
  commit();
}

export function getCustomModel(id: string): CustomModel | undefined {
  return state.custom.find((c) => c.id === id);
}
