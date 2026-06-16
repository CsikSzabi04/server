import { useState, type ChangeEvent } from 'react';
import { createPortal } from 'react-dom';
import type { MemoryApi } from '../hooks/useMemory';

// Full memory dashboard: edit the profile, prune facts (pin/delete), browse
// keywords, and export / import / clear everything. Rendered via a portal.
export default function MemoryView({ memory, onClose }: { memory: MemoryApi; onClose: () => void }) {
  const p = memory.profile;
  const [name, setName] = useState(p.name ?? '');
  const [nickname, setNickname] = useState(p.nickname ?? '');
  const [language, setLanguage] = useState(p.language ?? '');
  const [tone, setTone] = useState(p.tone ?? '');
  const [about, setAbout] = useState(p.about ?? '');
  const [interests, setInterests] = useState((p.interests ?? []).join(', '));
  const [saved, setSaved] = useState(false);

  const facts = memory.memories.filter((m) => m.kind !== 'keyword');
  const keywords = memory.memories.filter((m) => m.kind === 'keyword').sort((a, b) => b.weight - a.weight);

  const saveProfile = async () => {
    await memory.updateProfile({
      name: name || undefined,
      nickname: nickname || undefined,
      language: language || undefined,
      tone: tone || undefined,
      about: about || undefined,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  };

  const doExport = async () => {
    const data = await memory.exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'auri-memoria.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const doImport = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        void memory.importData(JSON.parse(String(r.result)));
      } catch {
        /* bad file */
      }
    };
    r.readAsText(f);
  };

  return createPortal(
    <div className="auth-overlay" onClick={onClose}>
      <div className="mem-modal" onClick={(e) => e.stopPropagation()}>
        <div className="mem-head">
          <span className="auth-title">MEMÓRIA</span>
          <button className="auth-close" onClick={onClose} aria-label="Bezárás">
            ✕
          </button>
        </div>

        <div className="mem-body">
          <section className="mem-sec">
            <h4>Profil {saved && <span className="mem-saved">mentve ✓</span>}</h4>
            <div className="mem-grid">
              <input className="auth-input" placeholder="név" value={name} onChange={(e) => setName(e.target.value)} />
              <input className="auth-input" placeholder="becenév" value={nickname} onChange={(e) => setNickname(e.target.value)} />
              <input className="auth-input" placeholder="nyelv" value={language} onChange={(e) => setLanguage(e.target.value)} />
              <input className="auth-input" placeholder="hangnem" value={tone} onChange={(e) => setTone(e.target.value)} />
            </div>
            <input className="auth-input" placeholder="érdeklődés (vesszővel)" value={interests} onChange={(e) => setInterests(e.target.value)} />
            <textarea className="auth-input mem-about" placeholder="rólam jegyzet" value={about} onChange={(e) => setAbout(e.target.value)} />
            <button className="auth-submit" onClick={() => void saveProfile()}>
              Profil mentése
            </button>
          </section>

          <section className="mem-sec">
            <h4>Tények / emlékek ({facts.length})</h4>
            {facts.length === 0 && <div className="archive-empty">Még nincs emlék.</div>}
            {facts.map((f) => (
              <div key={f.id ?? f.content} className="mem-fact">
                <span className="mem-fact-text">
                  {f.pinned && '📌 '}
                  {f.content}
                </span>
                <span className="mem-fact-actions">
                  <button title="rögzítés" onClick={() => f.id && void memory.pinMemory(f.id, !f.pinned)}>
                    {f.pinned ? '★' : '☆'}
                  </button>
                  <button title="törlés" onClick={() => f.id && void memory.removeMemory(f.id)}>
                    ✕
                  </button>
                </span>
              </div>
            ))}
          </section>

          <section className="mem-sec">
            <h4>Kulcsszavak ({keywords.length})</h4>
            {keywords.length === 0 && <div className="archive-empty">Még nincs kulcsszó.</div>}
            <div className="brain-chips">
              {keywords.slice(0, 60).map((k) => (
                <span key={k.id ?? k.content} className="brain-chip" title={`súly: ${k.weight}`}>
                  {k.content}
                </span>
              ))}
            </div>
          </section>

          <section className="mem-sec mem-controls">
            <button className="auth-switch" onClick={() => void doExport()}>
              ⬇ Export (JSON)
            </button>
            <label className="auth-switch mem-import">
              ⬆ Import
              <input type="file" accept="application/json" onChange={doImport} />
            </label>
            <button
              className="auth-switch mem-danger"
              onClick={() => {
                if (window.confirm('Tényleg törlöd az ÖSSZES emléket és a profilt?')) void memory.clearAll();
              }}
            >
              🗑 Összes törlése
            </button>
          </section>
        </div>
      </div>
    </div>,
    document.body,
  );
}
