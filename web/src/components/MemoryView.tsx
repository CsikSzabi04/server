import { useState, type ChangeEvent } from 'react';
import { createPortal } from 'react-dom';
import type { MemoryApi } from '../hooks/useMemory';
import { storageScope } from '../lib/storageScope';
import { exportAllMyData, deleteMyAccount } from '../lib/account';
import { redactSecrets } from '../lib/secrets';
import type { MemoryExport } from '../lib/memStore';
import type { Memory, Profile } from '../lib/memory';

const MAX_IMPORT_BYTES = 5 * 1024 * 1024; // an import file is untrusted input (SECURITY.md §10.5)

const KINDS = new Set<Memory['kind']>(['fact', 'keyword', 'doc', 'summary']);
const str = (v: unknown, max: number): string | undefined =>
  typeof v === 'string' && v.trim() ? v.slice(0, max) : undefined;

/** Validate an import file (shape, kinds, sizes) and blank any secrets in it — an export
 *  made before the secret filter existed must not bring passwords back (§10.5, §13.2). */
function sanitizeImport(raw: unknown): MemoryExport | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  if (!Array.isArray(r.memories) && (!r.profile || typeof r.profile !== 'object')) return null;
  const p = (r.profile && typeof r.profile === 'object' ? r.profile : {}) as Record<string, unknown>;
  const profile: Profile = {
    name: str(p.name, 120),
    nickname: str(p.nickname, 120),
    language: str(p.language, 40),
    tone: str(p.tone, 200),
    about: p.about !== undefined ? redactSecrets(str(p.about, 2000) ?? '') || undefined : undefined,
    interests: Array.isArray(p.interests)
      ? p.interests.filter((x): x is string => typeof x === 'string').slice(0, 50).map((x) => x.slice(0, 80))
      : undefined,
  };
  const memories: Memory[] = (Array.isArray(r.memories) ? r.memories : [])
    .slice(0, 5000)
    .filter((m): m is Record<string, unknown> => !!m && typeof m === 'object' && typeof (m as Record<string, unknown>).content === 'string')
    .map((m) => ({
      kind: KINDS.has(m.kind as Memory['kind']) ? (m.kind as Memory['kind']) : 'fact',
      content: redactSecrets(String(m.content).slice(0, 4000)),
      weight: Math.min(100, Math.max(1, Math.round(Number(m.weight) || 1))),
      pinned: m.pinned === true,
      source: str(m.source, 120),
    }))
    .filter((m) => m.content.trim().length > 0);
  return { profile, memories };
}

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
  const [docBusy, setDocBusy] = useState(false);
  const [docErr, setDocErr] = useState<string | null>(null);
  const [optMsg, setOptMsg] = useState<string | null>(null);
  const [acctMsg, setAcctMsg] = useState<string | null>(null);
  const [acctBusy, setAcctBusy] = useState(false);
  const signedIn = storageScope() !== null;

  const facts = memory.memories.filter((m) => m.kind === 'fact' || m.kind === 'summary');
  const keywords = memory.memories.filter((m) => m.kind === 'keyword').sort((a, b) => b.weight - a.weight);
  const docNames = Array.from(
    new Set(memory.memories.filter((m) => m.kind === 'doc').map((m) => m.source || 'untitled')),
  );
  const docs = docNames.map((src) => ({
    src,
    count: memory.memories.filter((m) => m.kind === 'doc' && (m.source || 'untitled') === src).length,
  }));

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setDocBusy(true);
    setDocErr(null);
    for (const f of Array.from(files)) {
      try {
        await memory.addDocument(f);
      } catch (e) {
        setDocErr((e as Error).message);
      }
    }
    setDocBusy(false);
  };

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
    a.download = 'auri-memory.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // GDPR art. 15 + 20: everything stored for the account (chats included), as JSON.
  const doExportAll = async () => {
    setAcctBusy(true);
    setAcctMsg(null);
    try {
      const blob = await exportAllMyData();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `auri-adataim-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setAcctMsg('Letöltve. A fájl az összes adatodat tartalmazza — vigyázz rá.');
    } catch (err) {
      setAcctMsg((err as Error).message);
    } finally {
      setAcctBusy(false);
    }
  };

  // GDPR art. 17: delete the account and ALL of its data (needs typed confirmation).
  const doDeleteAccount = async () => {
    const typed = window.prompt(
      'A fiókod és MINDEN adatod (beszélgetések, memória, profil, BRAIN) véglegesen törlődik. ' +
        'Ez nem vonható vissza.\n\nA megerősítéshez írd be: TÖRLÉS',
    );
    if (typed?.trim().toUpperCase() !== 'TÖRLÉS') return;
    setAcctBusy(true);
    setAcctMsg(null);
    const err = await deleteMyAccount();
    setAcctBusy(false);
    if (err) {
      setAcctMsg(err);
      return;
    }
    window.alert('A fiókodat és minden adatodat töröltük.');
    window.location.assign('/'); // fresh start: no state of the deleted account stays in memory
  };

  const doImport = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_IMPORT_BYTES) {
      setOptMsg('Import file too large (max 5 MB)');
      window.setTimeout(() => setOptMsg(null), 2500);
      return;
    }
    const r = new FileReader();
    r.onload = () => {
      try {
        const clean = sanitizeImport(JSON.parse(String(r.result)));
        if (clean) void memory.importData(clean);
        else setOptMsg('Not an Auri memory export');
      } catch {
        setOptMsg('Unreadable import file');
      }
      window.setTimeout(() => setOptMsg(null), 2500);
    };
    r.readAsText(f);
  };

  return createPortal(
    <div className="auth-overlay" onClick={onClose}>
      <div className="mem-modal" onClick={(e) => e.stopPropagation()}>
        <div className="mem-head">
          <span className="auth-title">MEMORY</span>
          <span className="widget-sub mono" style={{ marginLeft: 'auto', marginRight: 12, opacity: 0.8 }}>
            {memory.memories.length} items ·{' '}
            {(memory.memories.reduce((s, m) => s + m.content.length, 0) / 1024).toFixed(1)} KB
          </span>
          <button className="auth-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="mem-body">
          <section className="mem-sec">
            <h4>Profile {saved && <span className="mem-saved">saved ✓</span>}</h4>
            <div className="mem-grid">
              <input className="auth-input" placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
              <input className="auth-input" placeholder="nickname" value={nickname} onChange={(e) => setNickname(e.target.value)} />
              <input className="auth-input" placeholder="language" value={language} onChange={(e) => setLanguage(e.target.value)} />
              <input className="auth-input" placeholder="tone" value={tone} onChange={(e) => setTone(e.target.value)} />
            </div>
            <input className="auth-input" placeholder="interests (comma-separated)" value={interests} onChange={(e) => setInterests(e.target.value)} />
            <textarea className="auth-input mem-about" placeholder="about me" value={about} onChange={(e) => setAbout(e.target.value)} />
            <button className="auth-submit" onClick={() => void saveProfile()}>
              Save profile
            </button>
          </section>

          <section className="mem-sec">
            <h4>Facts / memories ({facts.length})</h4>
            {facts.length === 0 && <div className="archive-empty">No memories yet.</div>}
            {facts.map((f) => (
              <div key={f.id ?? f.content} className="mem-fact">
                <span className="mem-fact-text">
                  {f.pinned && '📌 '}
                  {f.content}
                </span>
                <span className="mem-fact-actions">
                  <button title="pin" onClick={() => f.id && void memory.pinMemory(f.id, !f.pinned)}>
                    {f.pinned ? '★' : '☆'}
                  </button>
                  <button title="delete" onClick={() => f.id && void memory.removeMemory(f.id)}>
                    ✕
                  </button>
                </span>
              </div>
            ))}
          </section>

          <section className="mem-sec">
            <h4>Documents ({docs.length})</h4>
            <label
              style={{
                display: 'block',
                textAlign: 'center',
                padding: '14px',
                cursor: 'pointer',
                border: '1px dashed rgba(31,229,255,0.4)',
                borderRadius: '4px',
                color: 'var(--accent)',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '0.72rem',
                marginBottom: '8px',
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                void handleFiles(e.dataTransfer.files);
              }}
            >
              {docBusy ? 'Processing…' : '📎 Drop a file here, or click (.txt, .md, .json, .csv)'}
              <input
                type="file"
                multiple
                accept=".txt,.md,.markdown,.json,.csv,.log,.text"
                style={{ display: 'none' }}
                onChange={(e) => void handleFiles(e.target.files)}
              />
            </label>
            {docErr && <div className="auth-err">{docErr}</div>}
            {docs.length === 0 && <div className="archive-empty">No documents uploaded yet.</div>}
            {docs.map((d) => (
              <div key={d.src} className="mem-fact">
                <span className="mem-fact-text">
                  📄 {d.src} <span style={{ opacity: 0.6 }}>· {d.count} chunks</span>
                </span>
                <span className="mem-fact-actions">
                  <button title="delete" onClick={() => void memory.removeDoc(d.src)}>
                    ✕
                  </button>
                </span>
              </div>
            ))}
          </section>

          <section className="mem-sec">
            <h4>Keywords ({keywords.length})</h4>
            {keywords.length === 0 && <div className="archive-empty">No keywords yet.</div>}
            <div className="brain-chips">
              {keywords.slice(0, 60).map((k) => (
                <span key={k.id ?? k.content} className="brain-chip" title={`weight: ${k.weight}`}>
                  {k.content}
                </span>
              ))}
            </div>
          </section>

          <section className="mem-sec mem-controls">
            <button
              className="auth-switch"
              onClick={async () => {
                const r = await memory.optimize();
                setOptMsg(r.removed ? `Optimized — merged/pruned ${r.removed}` : 'Already optimal');
                window.setTimeout(() => setOptMsg(null), 2500);
              }}
            >
              ⚡ Optimize
            </button>
            {optMsg && <span className="mem-saved">{optMsg}</span>}
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
                if (window.confirm('Really delete ALL memories and the profile?')) void memory.clearAll();
              }}
            >
              🗑 Delete all
            </button>
          </section>

          {signedIn && (
            <section className="mem-sec mem-controls">
              <h4 style={{ width: '100%', margin: 0 }}>Fiók és adatok</h4>
              <button className="auth-switch" disabled={acctBusy} onClick={() => void doExportAll()}>
                ⬇ Minden adatom letöltése (JSON)
              </button>
              <button className="auth-switch mem-danger" disabled={acctBusy} onClick={() => void doDeleteAccount()}>
                ⚠ Fiók végleges törlése
              </button>
              {acctMsg && <span className="mem-saved">{acctMsg}</span>}
              <a className="auth-switch" href="/adatvedelem.html" target="_blank" rel="noopener">
                Adatkezelési tájékoztató
              </a>
            </section>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
