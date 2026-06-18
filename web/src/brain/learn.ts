// learn.ts — the incremental, offline "literal brain" learner (BRAIN.md part II).
// Pure TypeScript, no deps, cheap & incremental. From the text it observes it
// builds, per stage:
//   Stage 2 — characters: charFreq + char→next-char transitions (+ babble()).
//   Stage 3 — words: per-word provenance (count, firstSeen, lastSeen, sources).
//   Stage 4 — associations: word→next-word transitions (Markov) (+ generate()).
//   Stage 5 — Q→A: remembers question→answer turns and recalls the closest one.
// (Stage 6 — a tiny in-browser net via tfjs — is intentionally NOT here; it needs
//  a dependency, which only AI-3 may install when requested.)
import { extractKeywords } from '../lib/memory';
import type { BrainPersistState, BrainStage } from './contracts';
import { stemSet } from './seed/stem';

const WORD_RE = /[\p{L}\p{N}']{2,}/gu;

/** Unicode-aware word tokenizer (Hungarian + English). */
export function tokenize(text: string): string[] {
  return text.toLowerCase().match(WORD_RE) ?? [];
}
/** Letters/digits of a text, lowercased (Stage 2). */
function letters(text: string): string[] {
  return Array.from(text.toLowerCase()).filter((c) => /[\p{L}\p{N}]/u.test(c));
}

// Capacity of the in-memory model. The Maps give O(1) (microsecond) lookups, so the
// limit is RAM, not speed. Raised to 2.2M so the bulk (~1.05M) + self-build (+700k)
// vocabulary all fits with headroom. (Bulk/self-build is NOT persisted — regenerated.)
const VOCAB_CAP = 2_200_000;
const QA_CAP = 2_000;

export interface WordMeta {
  count: number;
  firstSeen: string;
  lastSeen: string;
  sources: string[];
}
export interface QAPattern {
  q: string;
  a: string;
  keys: string[];
}

function inc(map: Map<string, Map<string, number>>, a: string, b: string, by = 1): void {
  let m = map.get(a);
  if (!m) map.set(a, (m = new Map()));
  m.set(b, (m.get(b) ?? 0) + by);
}
function weightedPick(m: Map<string, number> | undefined): string | undefined {
  if (!m || m.size === 0) return undefined;
  let total = 0;
  for (const c of m.values()) total += c;
  let r = Math.random() * total;
  for (const [k, c] of m) {
    r -= c;
    if (r <= 0) return k;
  }
  return undefined;
}

export class BrainLearner {
  words = new Map<string, WordMeta>(); // Stage 3
  transitions = new Map<string, Map<string, number>>(); // Stage 4: forward A→B (Markov)
  reverse = new Map<string, Map<string, number>>(); // Stage 4: backward B→A (for both-way recall)
  charFreq = new Map<string, number>(); // Stage 2
  charNext = new Map<string, Map<string, number>>(); // Stage 2
  qa: QAPattern[] = []; // Stage 5
  trainSteps = 0;

  static from(state: BrainPersistState | null): BrainLearner {
    const l = new BrainLearner();
    if (state) {
      if (state.words) {
        for (const [w, m] of Object.entries(state.words)) {
          l.words.set(w, {
            count: m.count ?? 1,
            firstSeen: m.firstSeen ?? '',
            lastSeen: m.lastSeen ?? '',
            sources: m.sources ?? [],
          });
        }
      } else if (state.vocab) {
        // legacy snapshot: only counts
        for (const [w, c] of Object.entries(state.vocab)) {
          l.words.set(w, { count: c, firstSeen: '', lastSeen: '', sources: [] });
        }
      }
      for (const [w, nexts] of Object.entries(state.transitions ?? {})) {
        const m = new Map<string, number>();
        for (const [n, c] of Object.entries(nexts)) m.set(n, c);
        l.transitions.set(w, m);
      }
      for (const [c, n] of Object.entries(state.charFreq ?? {})) l.charFreq.set(c, n);
      for (const [c, nexts] of Object.entries(state.charNext ?? {})) {
        const m = new Map<string, number>();
        for (const [n, k] of Object.entries(nexts)) m.set(n, k);
        l.charNext.set(c, m);
      }
      if (state.qa) l.qa = state.qa.slice(-QA_CAP);
      l.trainSteps = state.trainSteps ?? 0;
    }
    // legacy backfill: derive char frequencies from known words if missing
    if (l.charFreq.size === 0) {
      for (const w of l.words.keys()) for (const c of letters(w)) l.charFreq.set(c, (l.charFreq.get(c) ?? 0) + 1);
    }
    l.rebuildReverse(); // backward index is derived (not persisted → small snapshot)
    return l;
  }

  /** Rebuild the backward adjacency (B→A) from the forward transitions. Cheap, O(edges). */
  rebuildReverse(): void {
    this.reverse = new Map();
    for (const [a, m] of this.transitions) for (const [b, c] of m) inc(this.reverse, b, a, c);
  }

  /** Observe one text: grows chars (S2), words+provenance (S3), transitions (S4). */
  observe(text: string, source = 'chat'): { newWords: number } {
    const now = new Date().toISOString();
    const ws = tokenize(text);
    let newWords = 0;
    for (const w of ws) {
      const meta = this.words.get(w);
      if (!meta) {
        if (this.words.size < VOCAB_CAP) {
          this.words.set(w, { count: 1, firstSeen: now, lastSeen: now, sources: [source] });
          newWords++;
        }
      } else {
        meta.count++;
        meta.lastSeen = now;
        if (!meta.sources.includes(source) && meta.sources.length < 6) meta.sources.push(source);
      }
    }
    for (let i = 0; i + 1 < ws.length; i++) {
      inc(this.transitions, ws[i], ws[i + 1]); // forward A→B
      inc(this.reverse, ws[i + 1], ws[i]); // backward B→A → instant both-way recall
    }

    const cs = letters(text);
    for (let i = 0; i < cs.length; i++) {
      this.charFreq.set(cs[i], (this.charFreq.get(cs[i]) ?? 0) + 1);
      if (i + 1 < cs.length) inc(this.charNext, cs[i], cs[i + 1]);
    }
    this.trainSteps++;
    return { newWords };
  }

  /** Fast BULK path: learn an already-tokenized word sequence (no regex, no char model).
   *  Updates vocabulary (S3) + forward/backward transitions (S4). For seeding a large
   *  vocabulary efficiently. Tokens are assumed lowercased. */
  ingestTokens(tokens: string[], source = 'bulk'): void {
    let prev: string | undefined;
    for (const w of tokens) {
      const meta = this.words.get(w);
      if (!meta) {
        // empty timestamps: bulk words carry no provenance (saves RAM; excluded from
        // recentWords and from persistence — see toState()).
        if (this.words.size < VOCAB_CAP) this.words.set(w, { count: 1, firstSeen: '', lastSeen: '', sources: [source] });
      } else {
        meta.count++;
      }
      if (prev) {
        inc(this.transitions, prev, w);
        inc(this.reverse, w, prev);
      }
      prev = w;
    }
    this.trainSteps++;
  }

  /** Observe a whole chat turn: learns the words AND the Q→A mapping (Stage 5). */
  observeTurn(userText: string, assistantText: string, source = 'chat'): { newWords: number } {
    const q = userText.trim();
    const a = assistantText.trim();
    if (q && a) {
      this.qa.push({ q: q.slice(0, 300), a: a.slice(0, 1200), keys: extractKeywords(q, 10) });
      if (this.qa.length > QA_CAP) this.qa.splice(0, this.qa.length - QA_CAP);
    }
    const r1 = this.observe(userText, source);
    const r2 = this.observe(assistantText, source);
    this.trainSteps -= 1; // count a turn as one step (observe ran twice)
    return { newWords: r1.newWords + r2.newWords };
  }

  /** Back-compat view: word → count (derived from the richer `words` map).
   *  Kept so existing consumers (e.g. brain-bridge) that read `.vocab` still work. */
  get vocab(): Map<string, number> {
    const m = new Map<string, number>();
    for (const [w, meta] of this.words) m.set(w, meta.count);
    return m;
  }

  get vocabSize(): number {
    return this.words.size;
  }
  get charCount(): number {
    return this.charFreq.size;
  }
  get assocSize(): number {
    let n = 0;
    for (const m of this.transitions.values()) n += m.size;
    return n;
  }
  get qaCount(): number {
    return this.qa.length;
  }

  /**
   * Both-direction neighbours of a concept — successors (A→B) ∪ predecessors (B→A),
   * strongest first. O(degree) Map access = microseconds, regardless of total size.
   * This is the "knows the links back and forth, instantly" capability.
   */
  neighbors(word: string, limit = 16): { word: string; weight: number; dir: 'out' | 'in' | 'both' }[] {
    const w = word.toLowerCase();
    const acc = new Map<string, { out: number; in: number }>();
    const bump = (k: string, field: 'out' | 'in', c: number) => {
      const e = acc.get(k) ?? { out: 0, in: 0 };
      e[field] += c;
      acc.set(k, e);
    };
    for (const [b, c] of this.transitions.get(w) ?? []) bump(b, 'out', c);
    for (const [b, c] of this.reverse.get(w) ?? []) bump(b, 'in', c);
    return [...acc.entries()]
      .map(([n, v]) => ({
        word: n,
        weight: v.out + v.in,
        dir: (v.out && v.in ? 'both' : v.out ? 'out' : 'in') as 'out' | 'in' | 'both',
      }))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, limit);
  }

  /** Most recently learned words first — for the "new word ✦" readout. */
  recentWords(limit = 8): { word: string; firstSeen: string; sources: string[] }[] {
    return [...this.words.entries()]
      .filter(([, m]) => m.firstSeen)
      .sort((a, b) => (a[1].firstSeen < b[1].firstSeen ? 1 : -1))
      .slice(0, limit)
      .map(([word, m]) => ({ word, firstSeen: m.firstSeen, sources: m.sources }));
  }

  private startWord(): string | undefined {
    let best: string | undefined;
    let bestCount = -1;
    let i = 0;
    for (const [w, m] of this.words) {
      if (m.count > bestCount) {
        best = w;
        bestCount = m.count;
      }
      if (++i > 600) break;
    }
    return best;
  }

  /** Stage 4: Markov word-walk from what it has learned. */
  generate(seed: string | undefined, maxWords = 24): string {
    let cur: string | undefined = seed && this.words.has(seed.toLowerCase()) ? seed.toLowerCase() : this.startWord();
    if (!cur) return '';
    const out: string[] = [];
    for (let i = 0; i < maxWords && cur; i++) {
      out.push(cur);
      cur = weightedPick(this.transitions.get(cur));
    }
    return out.join(' ');
  }

  /** Stage 2: character-level babble — letters learning to clump into word-like
   *  forms. Pure proof that the brain learned the alphabet from your own text. */
  babble(maxChars = 48): string {
    let cur = weightedPick(this.charFreq);
    if (!cur) return '';
    const out: string[] = [];
    for (let i = 0; i < maxChars && cur; i++) {
      out.push(cur);
      cur = weightedPick(this.charNext.get(cur));
      if (Math.random() < 0.13) out.push(' '); // occasional word break
    }
    return out.join('').replace(/\s+/g, ' ').trim();
  }

  /** Stage 5: recall the closest past answer for a question (retrieval-composed). */
  recall(query: string): string | null {
    if (this.qa.length === 0) return null;
    // Stem both sides so inflected forms still match ("futás" ~ "futok" ~ "fut").
    const qk = stemSet(extractKeywords(query, 12));
    if (qk.size === 0) return null;
    let best: QAPattern | null = null;
    let bestScore = 0;
    for (const p of this.qa) {
      const pk = stemSet(p.keys);
      let hits = 0;
      for (const k of pk) if (qk.has(k)) hits++;
      const score = pk.size ? hits / Math.max(qk.size, pk.size) : 0;
      if (score > bestScore) {
        bestScore = score;
        best = p;
      }
    }
    return best && bestScore >= 0.34 ? best.a : null;
  }

  /**
   * M4 — consolidation ("sleep"): dedupe near-identical Q→A and trim each word's
   * transitions to its top-K strongest. Keeps the model lean, fast and focused at a
   * large corpus WITHOUT deleting vocabulary, so the 3D graph stays dense. Idempotent.
   */
  consolidate(topK = 24): { qaRemoved: number; edgesTrimmed: number } {
    // 1) dedupe Q→A by stemmed key-set + answer (newer occurrence wins its slot)
    const slot = new Map<string, number>();
    const kept: QAPattern[] = [];
    let qaRemoved = 0;
    for (const p of this.qa) {
      const sig = [...stemSet(p.keys)].sort().join('|') + '::' + p.a.slice(0, 48);
      const at = slot.get(sig);
      if (at !== undefined) {
        kept[at] = p;
        qaRemoved++;
      } else {
        slot.set(sig, kept.length);
        kept.push(p);
      }
    }
    this.qa = kept;
    // 2) trim transitions to the top-K strongest per source word (long-tail noise out)
    let edgesTrimmed = 0;
    for (const [w, nexts] of this.transitions) {
      if (nexts.size <= topK) continue;
      const top = [...nexts.entries()].sort((a, b) => b[1] - a[1]).slice(0, topK);
      edgesTrimmed += nexts.size - top.length;
      this.transitions.set(w, new Map(top));
    }
    if (edgesTrimmed > 0) this.rebuildReverse(); // keep the backward index consistent
    return { qaRemoved, edgesTrimmed };
  }

  /** Best local answer: a recalled Q→A if it fits, otherwise a Markov generation. */
  respond(query: string, maxWords = 24): string {
    const recalled = this.recall(query);
    if (recalled) return recalled;
    const qWords = tokenize(query);
    const seed = qWords.find((w) => this.transitions.has(w)) ?? qWords.find((w) => this.words.has(w));
    return this.generate(seed, maxWords);
  }

  /** Compact, serializable snapshot for persistence (AI-3 brainStore). */
  toState(): BrainPersistState {
    // Bulk-seeded words (procedural vocabulary) are NOT persisted — they are
    // regenerated deterministically on load. This keeps the saved snapshot small and
    // fast even with a ~1M-word brain. A bulk word becomes "real" (and persisted) the
    // moment chat/docs reinforce it (a non-'bulk' source gets added).
    const isBulk = (m: WordMeta) => m.sources.length > 0 && m.sources.every((s) => s.startsWith('bulk'));
    const vocab: Record<string, number> = {};
    const words: Record<string, { count: number; firstSeen: string; lastSeen: string; sources: string[] }> = {};
    const persisted = new Set<string>();
    for (const [w, m] of this.words) {
      if (isBulk(m)) continue;
      persisted.add(w);
      vocab[w] = m.count; // legacy mirror for back-compat
      words[w] = { count: m.count, firstSeen: m.firstSeen, lastSeen: m.lastSeen, sources: m.sources };
    }
    const transitions: Record<string, Record<string, number>> = {};
    for (const [w, m] of this.transitions) {
      if (!persisted.has(w)) continue;
      const o: Record<string, number> = {};
      for (const [n, c] of m) if (persisted.has(n)) o[n] = c;
      if (Object.keys(o).length) transitions[w] = o;
    }
    const charFreq: Record<string, number> = {};
    for (const [c, n] of this.charFreq) charFreq[c] = n;
    const charNext: Record<string, Record<string, number>> = {};
    for (const [c, m] of this.charNext) {
      const o: Record<string, number> = {};
      for (const [n, k] of m) o[n] = k;
      charNext[c] = o;
    }
    return {
      vocab,
      words,
      transitions,
      charFreq,
      charNext,
      qa: this.qa,
      trainSteps: this.trainSteps,
      updatedAt: new Date().toISOString(),
    };
  }
}

const STAGE_LABELS = [
  'Observing', // 0 — memory only
  'Listening', // 1 — first turns seen
  'Letters', // 2 — learned the alphabet (char model)
  'Words', // 3 — solid vocabulary
  'Associations', // 4 — word transitions
  'Phrasing', // 5 — Q→A patterns
  'Local network', // 6 — on-device net (future, tfjs)
];

/** Derive the learning stage + autonomy from the learner's size/coverage. */
export function deriveStage(
  vocab: number,
  assoc: number,
  trainSteps: number,
  charCount = 0,
  qaCount = 0,
): { stage: BrainStage; label: string; autonomyPct: number } {
  let stage: BrainStage = 0;
  if (trainSteps > 0) stage = 1;
  if (charCount >= 15) stage = 2;
  if (vocab >= 120) stage = 3;
  if (assoc >= 200) stage = 4;
  if (qaCount >= 12 && assoc >= 400) stage = 5;
  const autonomyPct = Math.min(
    95,
    Math.round(
      (Math.min(1, vocab / 2000) * 0.4 + Math.min(1, assoc / 4000) * 0.4 + Math.min(1, qaCount / 120) * 0.2) * 100,
    ),
  );
  return { stage, label: STAGE_LABELS[stage], autonomyPct };
}
