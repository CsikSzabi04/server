import { useCallback, useEffect, useRef, useState } from 'react';
import { supabase } from '../lib/supabase';
import { setStorageScope } from '../lib/storageScope';
import { findProjectBySlug, kindIcon, type CodeProject } from '../lib/codeProjects';
import { buildRunDocument } from '../lib/codeRunner';
// React 18 dev builds (readable errors), inlined into previews — this lazy route only.
// Relative path on purpose: react's package "exports" blocks the deep `react/umd/…` import.
import reactUmd from '../../node_modules/react/umd/react.development.js?raw';
import reactDomUmd from '../../node_modules/react-dom/umd/react-dom.development.js?raw';
import '../styles/code.css';

type Phase = 'loading' | 'ready' | 'missing' | 'notweb';

// /code/<slug> — runs a Code Project like a dev server would: the compiled page lives in
// an iframe sandboxed WITHOUT allow-same-origin (public/code-frame.html), so the code
// Auri wrote can't touch this app's storage or session. Live reload: whenever the editor
// (another tab) saves the project, the page rebuilds and the frame restarts.
export default function CodeRunPage({ slug }: { slug: string }) {
  const [phase, setPhase] = useState<Phase>('loading');
  const [project, setProject] = useState<CodeProject | null>(null);
  const [doc, setDoc] = useState('');
  const [hint, setHint] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [showErrors, setShowErrors] = useState(false);
  const [frameKey, setFrameKey] = useState(0);
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const docRef = useRef('');
  const lastSig = useRef('');
  const timer = useRef<number | null>(null);

  const rebuild = useCallback(
    (force = false) => {
      const p = findProjectBySlug(slug);
      if (!p) {
        setPhase('missing');
        return;
      }
      const sig = `${p.id}|${p.updatedAt}|${p.files.length}`;
      if (!force && sig === lastSig.current) return;
      lastSig.current = sig;
      setProject(p);
      document.title = `${p.name} · Auri run`;
      const r = buildRunDocument(p, { react: reactUmd, reactDom: reactDomUmd });
      if (r.kind === 'notweb') {
        setHint(r.hint);
        setPhase('notweb');
        return;
      }
      docRef.current = r.html;
      setDoc(r.html);
      setErrors(r.errors);
      setPhase('ready');
      setFrameKey((k) => k + 1); // fresh frame = clean JS state, like a page reload
    },
    [slug],
  );

  useEffect(() => {
    let alive = true;
    // Projects are stored per identity: resolve who is signed in on this browser first
    // (this route renders without App, so useAuth hasn't set the scope).
    void (async () => {
      let uid: string | null = null;
      try {
        const res = await supabase?.auth.getSession();
        uid = res?.data.session?.user.id ?? null;
      } catch {
        /* offline / not configured → guest projects */
      }
      if (!alive) return;
      setStorageScope(uid);
      rebuild(true);
    })();

    // The editor runs in another tab → its saves arrive as `storage` events.
    const onStorage = (e: StorageEvent) => {
      if (e.key && !e.key.startsWith('auri.projects')) return;
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => rebuild(), 350);
    };
    // The frame asks for its page once it's ready, and reports runtime errors.
    const onMessage = (e: MessageEvent) => {
      const win = frameRef.current?.contentWindow;
      if (!win || e.source !== win) return;
      const d = e.data as { type?: string; message?: string } | null;
      if (d?.type === 'auri-frame-ready') win.postMessage({ type: 'auri-run', html: docRef.current }, '*');
      else if (d?.type === 'auri-run-error' && d.message) setErrors((prev) => [...prev, String(d.message)].slice(-30));
    };
    window.addEventListener('storage', onStorage);
    window.addEventListener('message', onMessage);
    return () => {
      alive = false;
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('message', onMessage);
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [rebuild]);

  return (
    <div className="run-screen">
      <div className="run-bar">
        <span className="run-brand">◈ AURI RUN</span>
        <span className="run-name">
          {project ? `${kindIcon(project.kind)} ${project.name}` : slug}
        </span>
        <span className="run-url">/code/{slug}</span>
        {phase === 'ready' &&
          (errors.length ? (
            <button className="run-status run-status--err" onClick={() => setShowErrors((v) => !v)}>
              ⚠ {errors.length} error{errors.length > 1 ? 's' : ''}
            </button>
          ) : (
            <span className="run-status run-status--ok">● live</span>
          ))}
        <span className="run-spacer" />
        <button
          className="run-btn"
          title="Restart"
          onClick={() => {
            setErrors([]);
            rebuild(true);
          }}
        >
          ↻
        </button>
        <a className="run-btn" href="/" title="Back to Auri">
          ✕
        </a>
      </div>

      {showErrors && errors.length > 0 && (
        <pre className="run-errors" onClick={() => setShowErrors(false)}>
          {errors.join('\n\n')}
        </pre>
      )}

      {phase === 'ready' && doc && (
        <iframe
          key={frameKey}
          ref={frameRef}
          className="run-frame"
          title={project?.name ?? 'preview'}
          src="/code-frame.html"
          sandbox="allow-scripts allow-forms allow-modals allow-popups"
        />
      )}
      {phase === 'loading' && <div className="run-msg">Building…</div>}
      {phase === 'missing' && (
        <div className="run-msg">
          No project called “{slug}” on this browser{' '}
          <span className="run-dim">(projects are stored per account — sign in with the same one)</span>.
        </div>
      )}
      {phase === 'notweb' && (
        <div className="run-msg">
          {project?.name} is a {project?.kind} project — it doesn’t run in the browser. Run it on your machine:
          <pre className="run-cmd">{hint}</pre>
        </div>
      )}
    </div>
  );
}
