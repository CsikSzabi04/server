import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import BrainScene, { type FocusTarget, type Stimulus, type ThoughtStep } from './BrainScene';
import BrainFallback2D from './BrainFallback2D';
import ErrorBoundary from '../components/ErrorBoundary';
import { useBrainView } from './useBrainView';
import { useReducedMotion } from './useReducedMotion';
import { useBrainLearning, tokenize, distilledCount } from '../brain';
import { ZONES, ZONE_ANCHORS, ZONE_BY_ID, describeSource, type ZoneId } from './anatomy';
import type { BrainNode } from './types';
import { isWebNode } from './types';
import './brain-view.css';
import CorePanel from '../core-client/CorePanel';

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
/** three r169 needs WebGL2 — a WebGL1-only device would crash the scene. The probe
 *  context is released right away so it doesn't count against the browser's limit. */
function webglSupported(): boolean {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2');
    if (!gl) return false;
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return true;
  } catch {
    return false;
  }
}
/** 1234 → "1,234", 18800 → "18.8k", 1880460 → "1.88M" */
function fmt(n: number | undefined): string {
  const v = n ?? 0;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e4) return `${(v / 1e3).toFixed(1)}k`;
  return v.toLocaleString();
}
const zoneStyle = (z: ZoneId): CSSProperties => ({ '--zc': ZONE_BY_ID[z].color }) as CSSProperties;
const ATLAS = ZONES.filter((z) => z.id !== 'proto');
const RIGHT_SIDE: ZoneId[] = ['world', 'programming', 'vision'];

interface HoverInfo {
  node: BrainNode;
  x: number;
  y: number;
}

// The /brain page: the grown brain in 3D + a HUD that shows what is REALLY inside —
// the atlas (real knowledge per lobe), the live chain of associations firing right
// now, and the learner's honest vitals. Click a neuron to see what it connects to.
export default function BrainPage({ onExit }: { onExit?: () => void }) {
  const { graph, layout, positions, isMock } = useBrainView();
  const { state: brainState, recentWords, ask: askBrain } = useBrainLearning();
  const reducedMotion = useReducedMotion();
  const webgl = useMemo(() => webglSupported(), []);
  const webCount = useMemo(() => graph.nodes.filter(isWebNode).length, [graph]);

  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [selected, setSelected] = useState<BrainNode | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [hoverZone, setHoverZone] = useState<ZoneId | null>(null);
  const [lockedZone, setLockedZone] = useState<ZoneId | null>(null);
  const [showProto, setShowProto] = useState(true);
  const [thought, setThought] = useState<ThoughtStep[]>([]);
  const [stimulus, setStimulus] = useState<Stimulus | null>(null);
  const [growKey, setGrowKey] = useState(0);
  const [panels, setPanels] = useState(false); // phones: atlas/vitals hidden until asked for
  const searchInput = useRef<HTMLInputElement>(null);

  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph]);
  const idByLabel = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of graph.nodes) if (layout.zones[n.id] !== 'proto') m.set(n.label.toLowerCase(), n.id);
    return m;
  }, [graph, layout]);
  // neighbours as drawn (strongest first) — what a neuron is wired to
  const adjacency = useMemo(() => {
    const m = new Map<string, { id: string; s: number }[]>();
    const push = (a: string, b: string, s: number) => {
      const arr = m.get(a) ?? [];
      arr.push({ id: b, s });
      m.set(a, arr);
    };
    for (const e of graph.edges) {
      push(e.a, e.b, e.strength ?? 0);
      push(e.b, e.a, e.strength ?? 0);
    }
    for (const arr of m.values()) arr.sort((x, y) => y.s - x.s);
    return m;
  }, [graph]);

  // keyboard: "/" search · Esc closes / deselects / unlocks
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = document.activeElement instanceof HTMLInputElement;
      if (e.key === '/' && !typing) {
        e.preventDefault();
        setSearchOpen(true);
      } else if (e.key === 'Escape') {
        setSearchOpen(false);
        setQuery('');
        setSelected(null);
        setLockedZone(null);
        (document.activeElement as HTMLElement | null)?.blur?.();
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
    () => (q ? graph.nodes.filter((n) => layout.zones[n.id] !== 'proto' && n.label.toLowerCase().includes(q)) : []),
    [q, graph, layout],
  );
  const highlightIds = useMemo(() => (q ? new Set(matches.map((n) => n.id)) : null), [q, matches]);

  const recent = useMemo(() => {
    try {
      return recentWords(5) ?? [];
    } catch {
      return [];
    }
  }, [recentWords, brainState.vocab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── ask the brain (offline): answer + the question's words fire in 3D ──
  const [ask, setAsk] = useState('');
  const [asked, setAsked] = useState('');
  const [answer, setAnswer] = useState('');
  const onAsk = (e: FormEvent) => {
    e.preventDefault();
    const text = ask.trim();
    if (!text) return;
    let a = '';
    try {
      a = askBrain(text) || '';
    } catch {
      a = '';
    }
    setAsked(text);
    setAnswer(a || '…még tanulok — kérdezz egyszerűbben, vagy beszélgess velem a chatben');
    const ids: string[] = [];
    for (const w of tokenize(text)) {
      const id = nodeById.has(`lex_${w}`) ? `lex_${w}` : idByLabel.get(w);
      if (id && !ids.includes(id)) ids.push(id);
    }
    if (ids.length) setStimulus({ ids: ids.slice(0, 8), nonce: Date.now() });
    setAsk('');
  };

  const exit =
    onExit ??
    (() => {
      if (window.location.hash) window.location.hash = '';
      else window.location.assign('/');
    });

  const selectById = useCallback(
    (id: string) => {
      const n = nodeById.get(id);
      if (n) setSelected(n);
    },
    [nodeById],
  );
  const onHover = useCallback((node: BrainNode | null, x: number, y: number) => setHover(node ? { node, x, y } : null), []);
  const onSelect = useCallback((node: BrainNode | null) => setSelected(node), []);
  const onThought = useCallback((steps: ThoughtStep[]) => setThought(steps), []);
  const onZoneClick = useCallback((z: ZoneId) => {
    setSelected(null);
    setLockedZone((cur) => (cur === z ? null : z));
  }, []);

  const focusZone = hoverZone ?? lockedZone;
  const focus: FocusTarget | null = useMemo(() => {
    if (selected && positions[selected.id]) return { key: `n:${selected.id}`, point: positions[selected.id], kind: 'node' };
    if (matches[0] && positions[matches[0].id]) return { key: `q:${matches[0].id}`, point: positions[matches[0].id], kind: 'node' };
    if (lockedZone) {
      const anchors = ZONE_ANCHORS[lockedZone];
      const side = RIGHT_SIDE.includes(lockedZone) ? 1 : -1;
      const a = anchors.find((x) => Math.sign(x.surface[0]) === side) ?? anchors[0];
      if (a) return { key: `z:${lockedZone}`, point: a.surface, kind: 'zone' };
    }
    return null;
  }, [selected, matches, lockedZone, positions]);

  // ── selected-neuron card data ──
  const card = useMemo(() => {
    if (!selected) return null;
    const zone = layout.zones[selected.id] ?? 'language';
    const links = (adjacency.get(selected.id) ?? [])
      .map((x) => nodeById.get(x.id))
      .filter((n): n is BrainNode => !!n && layout.zones[n.id] !== 'proto')
      .slice(0, 12);
    let says = '';
    if (!selected.id.startsWith('region:') && !selected.id.startsWith('ltr_')) {
      try {
        says = (askBrain(selected.label) || '').trim();
      } catch {
        says = '';
      }
    }
    if (says.length > 280) says = `${says.slice(0, 277)}…`;
    return { zone, links, degree: adjacency.get(selected.id)?.length ?? 0, says };
  }, [selected, layout, adjacency, nodeById, askBrain]);

  const stage = brainState.stage ?? 0;
  const realNeurons = graph.nodes.length - layout.counts.proto;

  return (
    <div className={`brainx-root${panels ? ' show-panels' : ''}`}>
      {webgl ? (
        <div className="brainx-canvas">
          {/* a context-creation / runtime failure falls back to the 2D map instead of a blank page */}
          <ErrorBoundary fallback={<BrainFallback2D graph={graph} />}>
          <BrainScene
            graph={graph}
            layout={layout}
            selectedId={selected?.id ?? null}
            focus={focus}
            focusZone={focusZone}
            highlightIds={highlightIds}
            stimulus={stimulus}
            showProto={showProto}
            growKey={growKey}
            reducedMotion={reducedMotion}
            onHover={onHover}
            onSelect={onSelect}
            onThought={onThought}
            onZoneClick={onZoneClick}
          />
          </ErrorBoundary>
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
        <span className="bx-title">neural culture</span>
        {isMock && <span className="brainx-demo">demo</span>}
      </header>

      <div className="bx-tools">
        <button onClick={() => setSearchOpen(true)} title="Search the mind (/)">
          ⌕ search
        </button>
        <button onClick={() => setGrowKey((k) => k + 1)} title="Replay the growth from the stem">
          ⟲ regrow
        </button>
        <button className="bx-only-mobile" onClick={() => setPanels((p) => !p)} aria-pressed={panels}>
          ◫ stats
        </button>
        <div className="bx-hint">drag · scroll · click a neuron or a lobe</div>
      </div>

      {searchOpen && (
        <div className="brainx-search">
          <input
            ref={searchInput}
            className="brainx-search-input"
            placeholder="search the mind…  (Esc to close)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {q && (
            <span className="brainx-search-count">
              {matches.length} match{matches.length === 1 ? '' : 'es'}
            </span>
          )}
        </div>
      )}

      {hover && !selected && (
        <div className="brainx-tooltip" style={{ left: hover.x + 16, top: hover.y + 16 }}>
          <div className="brainx-tt-label">{hover.node.label}</div>
          <div className="brainx-tt-zone" style={zoneStyle(layout.zones[hover.node.id] ?? 'language')}>
            <i /> {ZONE_BY_ID[layout.zones[hover.node.id] ?? 'language'].name} · {ZONE_BY_ID[layout.zones[hover.node.id] ?? 'language'].lobe}
          </div>
          <div className="brainx-tt-meta">
            {describeSource(hover.node.sources[0])} · {adjacency.get(hover.node.id)?.length ?? 0} links
            {hover.node.pinned ? ' · ★' : ''}
          </div>
        </div>
      )}

      {selected && card && (
        <aside className="bx-card" style={zoneStyle(card.zone)}>
          <button className="bx-card-x" onClick={() => setSelected(null)} aria-label="Close">
            ✕
          </button>
          <div className="bx-card-zone">
            <i /> {ZONE_BY_ID[card.zone].name} · {ZONE_BY_ID[card.zone].lobe}
          </div>
          <div className="bx-card-label">{selected.label}</div>
          <div className="bx-card-meta">
            {selected.kind} · weight {(selected.weight ?? 0).toFixed(1)} · {card.degree} links
            {selected.pinned ? ' · ★ pinned' : ''}
          </div>
          <div className="bx-card-src">
            learned from: {describeSource(selected.sources[0])}
            {selected.sources.length > 1 && ` +${selected.sources.length - 1}`}
          </div>
          {selected.sources[0] && isUrl(selected.sources[0]) && (
            <a className="bx-card-link" href={selected.sources[0]} target="_blank" rel="noreferrer" title={selected.sources[0]}>
              ↗ official docs · {hostOf(selected.sources[0])}
            </a>
          )}
          {card.links.length > 0 && (
            <div className="bx-card-sec">
              <h5>wired to</h5>
              <div className="bx-chips">
                {card.links.map((n) => (
                  <button key={n.id} className="bx-chip" style={zoneStyle(layout.zones[n.id])} onClick={() => setSelected(n)}>
                    {n.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {card.says && (
            <div className="bx-card-sec">
              <h5>the brain says</h5>
              <p className="bx-card-says">{card.says}</p>
            </div>
          )}
        </aside>
      )}

      {/* ── bottom HUD: what is really inside ───────────────────────────── */}
      <div className="bx-hud">
        <section className="bx-panel bx-atlas" onMouseLeave={() => setHoverZone(null)}>
          <h4>
            brain atlas <span>real knowledge per lobe</span>
          </h4>
          {ATLAS.map((z) => (
            <button
              key={z.id}
              className={`bx-atlas-row${focusZone === z.id ? ' is-on' : ''}${layout.counts[z.id] ? '' : ' is-empty'}`}
              style={zoneStyle(z.id)}
              title={z.blurb}
              onMouseEnter={() => setHoverZone(z.id)}
              onClick={() => onZoneClick(z.id)}
            >
              <i />
              <b>{z.name}</b>
              <em>{z.lobe}</em>
              <span>{fmt(layout.counts[z.id])}</span>
            </button>
          ))}
          <label className="bx-atlas-proto" title={ZONE_BY_ID.proto.blurb}>
            <input type="checkbox" checked={showProto} onChange={(e) => setShowProto(e.target.checked)} />
            proto substrate <em>synthetic</em>
            <span>{fmt(layout.counts.proto)}</span>
          </label>
        </section>

        <section className="bx-center">
          <div className="bx-thought" aria-live="polite">
            <span className="bx-thought-tag">{stimulus && Date.now() - stimulus.nonce < 12000 ? 'associating' : 'thinking'}</span>
            {thought.length === 0 ? (
              <span className="bx-thought-idle">
                {reducedMotion ? 'impulses paused (reduced motion) — click a neuron to explore' : 'waiting for the first impulse…'}
              </span>
            ) : (
              thought.slice(-6).map((s, i) => (
                <Fragment key={`${s.id}-${i}`}>
                  {i > 0 && <span className="bx-arrow">→</span>}
                  <button className="bx-thought-word" style={zoneStyle(s.zone)} onClick={() => selectById(s.id)}>
                    {s.label}
                  </button>
                </Fragment>
              ))
            )}
          </div>
          {answer && (
            <div className="bx-answer">
              <div className="bx-answer-q">
                ❯ {asked}
                <button onClick={() => setAnswer('')} aria-label="Dismiss">
                  ✕
                </button>
              </div>
              {answer}
            </div>
          )}
          <form className="bx-ask" onSubmit={onAsk}>
            <input
              className="bx-ask-input"
              placeholder="ask the brain — offline · its words will fire"
              value={ask}
              onChange={(e) => setAsk(e.target.value)}
            />
          </form>
        </section>

        <section className="bx-panel bx-vitals" title="The local learner — grows offline, no API key">
          <h4>
            stage {stage} <span>{brainState.stageLabel}</span>
          </h4>
          <div className="bx-stages" aria-label={`stage ${stage} of 6`}>
            {[0, 1, 2, 3, 4, 5, 6].map((s) => (
              <i key={s} className={s <= stage ? 'on' : ''} />
            ))}
          </div>
          <div className="bx-auto">
            <span>autonomy</span>
            <div className="bx-bar">
              <div style={{ width: `${brainState.autonomyPct ?? 0}%` }} />
            </div>
            <b>{brainState.autonomyPct ?? 0}%</b>
          </div>
          <dl className="bx-nums">
            <div>
              <dt>neurons shown</dt>
              <dd>{fmt(realNeurons)}</dd>
            </div>
            <div>
              <dt>words known</dt>
              <dd>{fmt(brainState.vocab)}</dd>
            </div>
            <div>
              <dt>synapses</dt>
              <dd>{fmt(brainState.associations)}</dd>
            </div>
            <div>
              <dt>Q→A memories</dt>
              <dd>{fmt(brainState.qaPatterns)}</dd>
            </div>
            <div>
              <dt>from web</dt>
              <dd className="is-web">{fmt(webCount)}</dd>
            </div>
            <div>
              <dt>from model</dt>
              <dd>{fmt(distilledCount())}</dd>
            </div>
          </dl>
          {recent.length > 0 && (
            <div className="bx-recent">
              <span>newest</span>
              {recent.map((r) => (
                <em key={r.word} title={r.sources.map(describeSource).join(', ')}>
                  {r.word}
                </em>
              ))}
            </div>
          )}
          <CorePanel />
        </section>
      </div>
    </div>
  );
}
