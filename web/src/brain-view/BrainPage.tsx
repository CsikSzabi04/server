import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import BrainScene from './BrainScene';
import BrainFallback2D from './BrainFallback2D';
import { useBrainView } from './useBrainView';
import { useReducedMotion } from './useReducedMotion';
import { useBrainLearning } from '../brain';
import type { BrainNode } from './types';
import { isWebNode } from './types';
import './brain-view.css';

// Programming / doc nodes carry the official source URL in sources[0] (AI-1).
// Render it as a clickable link to the docs so the brain's knowledge is traceable.
function isUrl(s: string): boolean {
  return /^https?:\/\//i.test(s);
}
function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function webglSupported(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
  } catch {
    return false;
  }
}

interface HoverInfo {
  node: BrainNode;
  x: number;
  y: number;
}

// The /brain page: full-screen 3D neural map. Only persistent chrome is the
// AuriGPT wordmark + hamburger (back). Hover-tooltip, click-card, the "/" search
// overlay and a tiny stage readout are transient/minimal.
export default function BrainPage({ onExit }: { onExit?: () => void }) {
  const { graph, positions, isMock } = useBrainView();
  const { state: brainState, babble, recentWords, ask: askBrain } = useBrainLearning();
  const reducedMotion = useReducedMotion();
  const webgl = useMemo(() => webglSupported(), []);
  // How much the brain has learned from the web (grows as the askPipeline stores
  // web hits as nodes; 0 until AI-1/AI-3 wire it, so harmless today).
  const webCount = useMemo(() => graph.nodes.filter(isWebNode).length, [graph]);

  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [selected, setSelected] = useState<BrainNode | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const searchInput = useRef<HTMLInputElement>(null);

  // "/" opens search, Esc closes it (and deselects). (B7)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== searchInput.current) {
        e.preventDefault();
        setSearchOpen(true);
      } else if (e.key === 'Escape') {
        setSearchOpen(false);
        setQuery('');
        setSelected(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (searchOpen) searchInput.current?.focus();
  }, [searchOpen]);

  const q = query.trim().toLowerCase();
  const matches = useMemo(
    () => (q ? graph.nodes.filter((n) => n.label.toLowerCase().includes(q)) : []),
    [q, graph],
  );
  const highlightIds = useMemo(() => (q ? new Set(matches.map((n) => n.id)) : null), [q, matches]);

  // Local "speech area" readout — drawn from the engine (AI-1): letters/words/
  // links learned, the latest words (✦), and a babble sample (letters → words).
  // Guarded: these must NEVER throw and blank the whole 3D scene.
  const recent = useMemo(() => {
    try {
      return recentWords(4) ?? [];
    } catch {
      return [];
    }
  }, [recentWords, brainState.vocab]);
  const babbleSample = useMemo(() => {
    try {
      return babble(44) ?? '';
    } catch {
      return '';
    }
  }, [babble, brainState.vocab, brainState.chars]);

  // The "speech area": ask the brain and it answers from its OWN learned model
  // (reply() = personal facts + base phrasing; falls back to speak() = Markov).
  // Offline, no API key — empty until it has learned enough.
  const [ask, setAsk] = useState('');
  const [answer, setAnswer] = useState('');
  const onAsk = (e: FormEvent) => {
    e.preventDefault();
    const query = ask.trim();
    if (!query) return;
    let a = '';
    try {
      a = askBrain(query) || ''; // clean offline answer (knowledge + recall + links), never random Markov
    } catch {
      a = '';
    }
    setAnswer(a || '…még tanulok — kérdezz egyszerűbben, vagy beszélgess velem a chatben');
  };

  const exit =
    onExit ??
    (() => {
      if (window.location.hash) window.location.hash = '';
      else window.location.assign('/');
    });

  const focus: [number, number, number] | null = selected
    ? positions[selected.id] ?? null
    : matches[0]
      ? positions[matches[0].id] ?? null
      : null;

  return (
    <div className="brainx-root">
      {webgl ? (
        <div className="brainx-canvas">
          <BrainScene
            graph={graph}
            positions={positions}
            selectedId={selected?.id ?? null}
            focus={focus}
            highlightIds={highlightIds}
            reducedMotion={reducedMotion}
            onHover={(node, x, y) => setHover(node ? { node, x, y } : null)}
            onSelect={(node) => setSelected(node)}
          />
        </div>
      ) : (
        <BrainFallback2D graph={graph} />
      )}

      <header className="brainx-chrome">
        <button className="brainx-burger" onClick={exit} title="Back to AuriGPT" aria-label="Back to AuriGPT">
          ☰
        </button>
        <span className="brainx-brand">
          ◈ AURI<span className="brainx-brand-sub">GPT</span>
        </span>
        {isMock && <span className="brainx-demo">demo</span>}
      </header>

      {searchOpen && (
        <div className="brainx-search">
          <input
            ref={searchInput}
            className="brainx-search-input"
            placeholder="search the mind…  (Esc to close)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {q && <span className="brainx-search-count">{matches.length} match{matches.length === 1 ? '' : 'es'}</span>}
        </div>
      )}

      {hover && !selected && (
        <div className="brainx-tooltip" style={{ left: hover.x + 16, top: hover.y + 16 }}>
          <div className="brainx-tt-label">{hover.node.label}</div>
          <div className="brainx-tt-meta">
            {hover.node.kind} · w{hover.node.weight}
            {hover.node.pinned ? ' · ★' : ''}
          </div>
        </div>
      )}

      {selected && (
        <aside className="brainx-card">
          <button className="brainx-card-x" onClick={() => setSelected(null)} aria-label="Close">
            ✕
          </button>
          <div className="brainx-card-kind" style={{ color: selected.color }}>
            {selected.kind.toUpperCase()}
            {selected.pinned ? ' · ★ pinned' : ''}
          </div>
          <div className="brainx-card-label">{selected.label}</div>
          <div className="brainx-card-row">
            weight {selected.weight} · freshness {Math.round((selected.freshness ?? 0) * 100)}%
          </div>
          {selected.sources.length > 0 &&
            (isUrl(selected.sources[0]) ? (
              <a
                className="brainx-card-link"
                href={selected.sources[0]}
                target="_blank"
                rel="noreferrer"
                title={selected.sources[0]}
              >
                ↗ official docs · {hostOf(selected.sources[0])}
              </a>
            ) : (
              <div className="brainx-card-src">source: {selected.sources.join(', ')}</div>
            ))}
        </aside>
      )}

      <form className="brainx-ask" onSubmit={onAsk}>
        {answer && <div className="brainx-ask-answer">{answer}</div>}
        <input
          className="brainx-ask-input"
          placeholder="ask the brain — offline, no API…"
          value={ask}
          onChange={(e) => setAsk(e.target.value)}
        />
      </form>

      <div className="brainx-vitals" title="Local brain (BRAIN.md part II) — learns offline, no API key">
        <div className="brainx-vitals-stage">
          STAGE {brainState.stage ?? 0} · {brainState.autonomyPct ?? 0}% autonomy
        </div>
        <div className="brainx-vitals-row">
          letters {brainState.chars ?? 0} · words {brainState.vocab ?? 0} · links {brainState.associations ?? 0}
        </div>
        {recent.length > 0 && (
          <div className="brainx-vitals-recent">recent: {recent.map((r) => r.word).join(' ✦ ')}</div>
        )}
        {babbleSample && <div className="brainx-vitals-babble">babble: “{babbleSample}”</div>}
        {webCount > 0 && <div className="brainx-vitals-web">🌐 learned from web: {webCount} ✦</div>}
      </div>
    </div>
  );
}
