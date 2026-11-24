import { StrictMode, Suspense, lazy, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// HUD fonts, SELF-HOSTED (bundled from @fontsource) — no request to Google Fonts, so a
// visitor's IP is not sent to a third party just by opening the page (SECURITY.md §19.4).
// Same families/weights the old fonts.googleapis.com <link> loaded; incl. latin-ext (ő, ű).
import '@fontsource/orbitron/400.css';
import '@fontsource/orbitron/500.css';
import '@fontsource/orbitron/700.css';
import '@fontsource/orbitron/900.css';
import '@fontsource/share-tech-mono/400.css';
import '@fontsource/rajdhani/400.css';
import '@fontsource/rajdhani/500.css';
import '@fontsource/rajdhani/600.css';
import '@fontsource/rajdhani/700.css';
import '@fontsource/exo-2/300.css';
import '@fontsource/exo-2/400.css';
import '@fontsource/exo-2/500.css';
import '@fontsource/exo-2/600.css';
import './styles/hud.css';
import './styles/responsive.css';
import './styles/code.css'; // app-wide styles live here (sidebar/chat badges, code blocks) → eager

// AI-3 (BODY) — top-level routing. `/brain` (or `#brain`) renders AI-2's 3D brain
// page; every other path renders the existing App. App.tsx is left untouched.
// BrainPage is lazy-loaded so its heavy three.js chunk only downloads on that route.
const BrainPage = lazy(() => import('./brain-view/BrainPage'));
// AI-3 (BODY, Jarvis) — `/jarvis` or `#jarvis` (also `#jarvis&token=…` in dev) renders the HUD
// of the local Jarvis daemon (auri-jarvis, ws://127.0.0.1:8790). Lazy-loaded, App.tsx untouched.
const JarvisHud = lazy(() => import('./jarvis/JarvisHud'));
// Floating "download the desktop app" button (bottom-right) — only on the web AuriGPT.
const DownloadJarvis = lazy(() => import('./jarvis/DownloadJarvis'));
// The desktop app (daemon-served page): the HUD is home, `#brain` still opens the BRAIN.
// (the daemon injects <meta name="jarvis-token"> into the page it serves — any port)
const SERVED_BY_DAEMON = !!document.querySelector('meta[name="jarvis-token"]') || window.location.port === '8790';
// `/code/<project-slug>` runs a Code Project (web/React) in a sandboxed iframe, like a
// dev server. Lazy: its transpiler + inlined React only download on that route.
const CodeRunPage = lazy(() => import('./components/CodeRunPage'));

/** The project slug of a `/code/<slug>` path, else null. Checked BEFORE brain/jarvis. */
function codeRouteSlug(): string | null {
  const m = window.location.pathname.match(/^\/code\/([^/]+)\/?$/i);
  if (!m) return null;
  try {
    return decodeURIComponent(m[1]);
  } catch {
    return m[1];
  }
}

function isBrainRoute(): boolean {
  const hash = window.location.hash.replace(/^#\/?/, '').toLowerCase();
  const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
  return hash === 'brain' || path === '/brain' || path.endsWith('/brain');
}

function isJarvisRoute(): boolean {
  const hash = window.location.hash.replace(/^#\/?/, '').split(/[&?]/)[0].toLowerCase();
  const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
  return (SERVED_BY_DAEMON && !isBrainRoute()) || hash === 'jarvis' || path === '/jarvis' || path.endsWith('/jarvis');
}

// SPA-smooth return to the main app, from either a hash or a path entry.
function goHome(): void {
  const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
  if (path === '/brain' || path.endsWith('/brain') || path === '/jarvis' || path.endsWith('/jarvis')) {
    window.history.pushState(null, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  } else {
    window.location.hash = '';
  }
}

// Shown while the 3D chunk loads.
function BrainFallback() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'grid',
        placeItems: 'center',
        background: 'radial-gradient(ellipse at 50% 30%, #0a1626 0%, #04070d 70%)',
        color: '#cfeefe',
        fontFamily: "'Share Tech Mono', monospace",
        textAlign: 'center',
        padding: 24,
      }}
    >
      <div>
        <div style={{ color: '#1fe5ff', fontSize: '1.4rem', letterSpacing: '0.2em' }}>◈ /brain</div>
        <p style={{ marginTop: 12, opacity: 0.8 }}>Loading the neural map…</p>
      </div>
    </div>
  );
}

function Router() {
  const [brain, setBrain] = useState(isBrainRoute());
  const [jarvis, setJarvis] = useState(isJarvisRoute());
  const [codeSlug, setCodeSlug] = useState(codeRouteSlug());
  useEffect(() => {
    const onChange = () => {
      setBrain(isBrainRoute());
      setJarvis(isJarvisRoute());
      setCodeSlug(codeRouteSlug());
    };
    window.addEventListener('hashchange', onChange);
    window.addEventListener('popstate', onChange);
    return () => {
      window.removeEventListener('hashchange', onChange);
      window.removeEventListener('popstate', onChange);
    };
  }, []);

  // before `jarvis`: inside the desktop app every non-#brain path counts as the HUD
  if (codeSlug) {
    return (
      <Suspense fallback={<div style={{ position: 'fixed', inset: 0, background: '#04070d' }} />}>
        <CodeRunPage slug={codeSlug} />
      </Suspense>
    );
  }
  if (jarvis) {
    return (
      <Suspense fallback={<div style={{ position: 'fixed', inset: 0, background: '#04070d' }} />}>
        <JarvisHud onExit={SERVED_BY_DAEMON ? undefined : goHome} />
      </Suspense>
    );
  }
  if (!brain) {
    return (
      <>
        <App />
        {!SERVED_BY_DAEMON && (
          <Suspense fallback={null}>
            <DownloadJarvis />
          </Suspense>
        )}
      </>
    );
  }
  return (
    <Suspense fallback={<BrainFallback />}>
      <BrainPage onExit={goHome} />
    </Suspense>
  );
}

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <Router />
  </StrictMode>,
);
