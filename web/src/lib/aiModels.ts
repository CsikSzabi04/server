// The model catalog + live availability, for the composer's model picker.
//
//  - "Auto" + hosted: always selectable (the server's free fallback chain).
//  - Local Ollama models: only selectable when YOUR PC (local backend) is on —
//    probed via /api/models. When the PC is off they are shown but disabled.
//  - "Your keys" (BYO): the user's own providers, always usable (direct calls).
import { useEffect, useState } from 'react';
import { getPrefs, subscribePrefs, type CustomModel } from './modelStore';

export interface ModelOption {
  id: string;
  label: string;
  group: 'Auto & hosted' | 'Local (your PC)' | 'Your keys';
  available: boolean;
  detail?: string;
  custom?: CustomModel;
}

// Local Ollama models we ship. `forcedModelId` only returns these (selecting
// hosted/auto leaves the model unset so the server chain decides).
const OLLAMA = [
  { id: 'gemma2:2b', label: 'Gemma2 2B', detail: 'smart default' },
  { id: 'qwen2.5:1.5b', label: 'Qwen2.5 1.5B', detail: 'fast' },
  { id: 'smollm2', label: 'SmolLM2', detail: 'tiny' },
  { id: 'tinyllama', label: 'TinyLlama', detail: 'fastest' },
];
const OLLAMA_IDS = new Set(OLLAMA.map((o) => o.id));

const HOSTED = [
  { id: 'auto', label: 'Auto', detail: 'local → Groq → Gemini' },
  { id: 'groq', label: 'Groq Llama 3.3 70B', detail: 'via server (free)' },
  { id: 'gemini', label: 'Gemini 2.0 Flash', detail: 'via server (free)' },
];

/** Only Ollama selections force a specific model on the backend. */
export function forcedModelId(selectedId: string): string | undefined {
  return OLLAMA_IDS.has(selectedId) ? selectedId : undefined;
}

// ── live local availability (shared) ─────────────────────────────────────────
let localUp = false;
let localModels: string[] | null = null;
let probed = false;
const availListeners = new Set<() => void>();
const emitAvail = () => {
  for (const fn of availListeners) fn();
};

export async function probeLocal(): Promise<void> {
  try {
    const r = await fetch('/api/models', { cache: 'no-store', signal: AbortSignal.timeout(4000) });
    if (!r.ok) throw new Error(String(r.status));
    const j = (await r.json()) as { ollamaUp?: boolean; models?: string[] };
    localUp = !!j.ollamaUp;
    localModels = Array.isArray(j.models) ? j.models : null;
  } catch {
    localUp = false;
    localModels = null;
  }
  probed = true;
  emitAvail();
}

function installed(id: string): boolean {
  if (!localModels) return true; // backend up but list unknown → assume present
  const base = id.split(':')[0];
  return localModels.some((m) => m === id || m.startsWith(base));
}

export function buildOptions(): ModelOption[] {
  const opts: ModelOption[] = [];
  for (const h of HOSTED) {
    opts.push({ id: h.id, label: h.label, group: 'Auto & hosted', available: true, detail: h.detail });
  }
  for (const o of OLLAMA) {
    opts.push({
      id: o.id,
      label: o.label,
      group: 'Local (your PC)',
      available: localUp && installed(o.id),
      detail: probed && !localUp ? 'PC offline' : o.detail,
    });
  }
  for (const c of getPrefs().custom) {
    opts.push({ id: c.id, label: c.label, group: 'Your keys', available: true, detail: c.model, custom: c });
  }
  return opts;
}

/** Hook: live model options + current prefs, re-rendering on changes/probes. */
export function useModels() {
  const [, force] = useState(0);
  useEffect(() => {
    const rerender = () => force((x) => x + 1);
    availListeners.add(rerender);
    const unsub = subscribePrefs(rerender);
    void probeLocal();
    const id = window.setInterval(() => void probeLocal(), 15_000);
    return () => {
      availListeners.delete(rerender);
      unsub();
      window.clearInterval(id);
    };
  }, []);
  return { options: buildOptions(), prefs: getPrefs() };
}
