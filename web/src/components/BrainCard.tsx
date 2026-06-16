import type { MemoryApi } from '../hooks/useMemory';

// Floating "BRAIN" card shown when hovering the 3D core — a live readout of what
// Auri has learned. Styled like the auth/login card (glass + cyan glow).
export default function BrainCard({
  memory,
  conversationCount,
  onOpen,
}: {
  memory: MemoryApi;
  conversationCount: number;
  onOpen: () => void;
}) {
  const p = memory.profile;
  const facts = memory.memories.filter((m) => m.kind !== 'keyword');
  const keywords = memory.memories
    .filter((m) => m.kind === 'keyword')
    .sort((a, b) => b.weight - a.weight);
  const fullness = Math.min(100, Math.round((memory.memories.length / 60) * 100));
  const recent = facts.slice(0, 3);

  return (
    <div className="brain-card">
      <div className="brain-card-title">BRAIN</div>

      <div className="brain-row">
        <span>Felhasználó</span>
        <b>{p.name || 'ismeretlen'}</b>
      </div>
      {p.language && (
        <div className="brain-row">
          <span>Nyelv</span>
          <b>{p.language}</b>
        </div>
      )}

      <div className="brain-stats">
        <div>
          <b>{conversationCount}</b>
          <span>chat</span>
        </div>
        <div>
          <b>{facts.length}</b>
          <span>tény</span>
        </div>
        <div>
          <b>{keywords.length}</b>
          <span>kulcsszó</span>
        </div>
      </div>

      <div className="brain-bar">
        <div className="brain-bar-fill" style={{ width: `${fullness}%` }} />
      </div>
      <div className="brain-bar-label">memória {fullness}%</div>

      {keywords.length > 0 && (
        <div className="brain-chips">
          {keywords.slice(0, 8).map((k) => (
            <span
              key={k.id ?? k.content}
              className="brain-chip"
              style={{ fontSize: `${0.6 + Math.min(0.35, (k.weight - 1) * 0.07)}rem` }}
            >
              {k.content}
            </span>
          ))}
        </div>
      )}

      {recent.length > 0 && (
        <div className="brain-recent">
          <div className="brain-recent-h">Legutóbb tanult</div>
          {recent.map((r) => (
            <div key={r.id ?? r.content} className="brain-recent-item">
              • {r.content.length > 64 ? `${r.content.slice(0, 64)}…` : r.content}
            </div>
          ))}
        </div>
      )}

      <button className="brain-open" onClick={onOpen}>
        MEMÓRIA MEGNYITÁSA
      </button>
    </div>
  );
}
