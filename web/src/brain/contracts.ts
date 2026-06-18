// contracts.ts — the SHARED LANGUAGE for the BRAIN feature. AI-1 (MIND) owns it.
//
// AI-2 (3D /brain view) and AI-3 (persistence/integration) import TYPES from
// here and never invent their own. This file is pure types — no React, no
// runtime logic — so it's safe to import from anywhere.
//
// Import sites:
//   - types:  import type { BrainGraph, BrainStats, ... } from '../brain/contracts'
//   - hooks:  import { useBrainGraph, useBrainLearning } from '../brain'
//   - store:  AI-3 implements `BrainStore` in '../brain/brainStore'

// ── graph (what AI-2 renders in 3D) ──────────────────────────────────────────
export type BrainNodeKind = 'profile' | 'fact' | 'keyword' | 'doc' | 'summary';

export interface BrainNode {
  id: string;
  label: string;
  kind: BrainNodeKind;
  weight: number; // importance (memory weight; profile is high)
  freshness: number; // 0..1 — 1 = just learned, decays with age
  pinned: boolean;
  regionId: string; // cluster this node belongs to
  sources: string[]; // e.g. ['chat'] or ['notes.md']
  color: string; // display color derived from the region hue
}

export interface BrainEdge {
  a: string; // node id
  b: string; // node id
  strength: number; // 0..1
  dir: 0 | 1; // 0 = undirected (co-occurrence), 1 = a → b (e.g. Markov transition)
  fresh: boolean; // formed recently
}

export interface BrainRegion {
  id: string;
  label: string;
  hue: number; // 0..360
  centroid?: [number, number, number]; // optional 3D seed (AI-2 may set/use it)
  nodeIds: string[];
}

export interface BrainGraph {
  nodes: BrainNode[];
  edges: BrainEdge[];
  regions: BrainRegion[];
}

// ── web-learning (3.b: ask → brain-first → web → store) ──────────────────────
// A search result. Structurally identical to autolearn's Hit, so the two are
// interchangeable with no import coupling.
export interface WebHit {
  title: string;
  url: string;
  snippet: string;
}

// ── Stage 6 (BRAIN.md §20.6): the in-browser neural net's status (for the
// /brain "learning curve" panel). The net is optional + lazy; available=false
// simply means it isn't active and the rest of the brain works unchanged.
export interface Stage6Status {
  available: boolean;
  training: boolean;
  ready: boolean;
  trainSteps: number;
  loss: number[]; // loss per epoch — the learning curve
  vocab: number; // model vocabulary size
}

// A stored web fact: what the brain learned from a search result, with freshness
// metadata so brainCovers() can decide when to re-fetch.
export interface WebDoc {
  url: string;
  title: string;
  snippet: string;
  query: string; // the query that fetched it
  weight: number; // 1..5 from domain trust
  fetchedAt: string; // ISO — when it was learned
  ttlDays: number; // how long it stays "fresh"
}

// ── stats (the BRAIN-card / HUD numbers) ─────────────────────────────────────
export interface BrainStats {
  conversations: number;
  facts: number;
  keywords: number;
  docs: number;
  vocab: number; // unique words the local brain has seen
  fullnessPct: number; // 0..100
  lastLearnedAt: string | null;
}

// ── learning state (BRAIN.md part II — the "literal brain" stages) ────────────
// 0 = observe/memory (today) … 6 = local network (needs tfjs, later).
export type BrainStage = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export interface BrainState {
  stage: BrainStage;
  stageLabel: string;
  vocab: number; // unique words learned
  chars: number; // distinct characters learned (Stage 2)
  associations: number; // learned word→word transitions
  qaPatterns: number; // remembered question→answer turns (Stage 5)
  trainSteps: number; // turns observed
  autonomyPct: number; // 0..100 — how independent the local brain is
  updatedAt: string;
}

// ── hook result shapes (implemented in useBrainGraph.ts / useBrainLearning.ts) ─
export interface BrainGraphResult {
  graph: BrainGraph;
  stats: BrainStats;
  loading: boolean;
}

export interface BrainLearningResult {
  state: BrainState;
  /** Observe one chat turn to grow the local brain (incremental, cheap, offline). */
  observe: (userText: string, assistantText: string) => void;
  /** Reset the locally-learned language model (does NOT touch the memory store). */
  reset: () => void;
  /** The brain's OWN statistical (Markov) attempt at a reply — honest local
   *  generation, no model/network. Empty string until it has learned enough. */
  speak: (query: string) => string;
  /** Character-level babble (Stage 2 proof: letters clumping into word-like forms). */
  babble: (maxChars?: number) => string;
  /** Most recently learned words, newest first (for the "new word ✦" readout). */
  recentWords: (limit?: number) => { word: string; firstSeen: string; sources: string[] }[];
  /** Local-brain answer: personal facts (passed in) + the base brain's phrasing.
   *  Offline, no API key; empty if it can't say anything useful yet. */
  reply: (query: string, facts?: string[]) => string;
  /** Does the brain already cover this query (freshly)? Used for brain-first routing
   *  before a web search. Returns the offline answer when covered. */
  covers: (query: string, facts?: string[]) => { covered: boolean; answer: string };
  /** Learn from web search results: store source docs (region:web) + grow the
   *  vocabulary from the text. Closes the self-improvement loop (3.b). */
  learnWeb: (query: string, hits: WebHit[], pages?: string[]) => void;
  /** Stage 6 in-browser neural-net status (learning curve, readiness) for the
   *  /brain panel. available=false when the optional net isn't active. */
  stage6: () => Stage6Status;
  /** Hybrid H1 — the BRAIN KNOWLEDGE grounding block for a query (empty if nothing
   *  relevant). Injected into the model's system message so a small Ollama model
   *  answers grounded in our brain. `memories` is the personal memory list. */
  ground: (query: string, memories: import('../lib/memory').Memory[]) => string;
  /** Hybrid H2 — distil a MODEL answer into the brain (learn it so it can answer the
   *  same offline next time). Call after each model turn. */
  distill: (query: string, answer: string) => void;
  /** Hybrid H4 — the next topic the brain should study on its own (rotating pool), or
   *  null. The bridge asks the model about it and distils the answer. */
  studyTopic: () => string | null;
  /** The OFFLINE ask-bar answer (no API/model): a clean, topic-relevant sentence from
   *  what the brain knows + its links. '' only when it truly has nothing. */
  ask: (query: string) => string;
}

// ── arbiter (pure decision; AI-3 wires it into the chat behind a feature flag) ─
export type ArbiterRoute = 'retrieval' | 'local-brain' | 'local-model' | 'fallback';
export interface ArbiterDecision {
  route: ArbiterRoute;
  confidence: number; // 0..1
  reason: string;
}

// ── persistence contract (AI-3 implements this in brainStore.ts) ─────────────
// The compact, serializable snapshot of the local learner.
export interface BrainPersistState {
  vocab: Record<string, number>; // word → count (legacy mirror; always written)
  // richer per-word provenance (Stage 3) — optional for backward compatibility
  words?: Record<string, { count: number; firstSeen: string; lastSeen: string; sources: string[] }>;
  transitions: Record<string, Record<string, number>>; // word → next-word → count (Stage 4)
  charFreq?: Record<string, number>; // char → count (Stage 2)
  charNext?: Record<string, Record<string, number>>; // char → next-char → count (Stage 2)
  qa?: { q: string; a: string; keys: string[] }[]; // question→answer patterns (Stage 5)
  seedVersion?: number; // which embedded seed corpus inoculated this brain (idempotency)
  trainSteps: number;
  updatedAt: string;
}
export interface BrainStore {
  load: (userId: string | null) => Promise<BrainPersistState | null>;
  save: (userId: string | null, state: BrainPersistState) => Promise<void>;
  exportJSON: (userId: string | null) => Promise<BrainPersistState | null>;
  importJSON: (userId: string | null, data: BrainPersistState) => Promise<void>;
}
