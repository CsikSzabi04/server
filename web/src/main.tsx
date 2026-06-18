import { StrictMode, Suspense, lazy, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/hud.css';
import './styles/responsive.css';
import './styles/code.css'; // app-wide styles live here (sidebar/chat badges, code blocks) → eager

// AI-3 (BODY) — top-level routing. `/brain` (or `#brain`) renders AI-2's 3D brain
// page; every other path renders the existing App. App.tsx is left untouched.
// BrainPage is lazy-loaded so its heavy three.js chunk only downloads on that route.
const BrainPage = lazy(() => import('./brain-view/BrainPage'));

function isBrainRoute(): boolean {
  const hash = window.location.hash.replace(/^#\/?/, '').toLowerCase();
  const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
  return hash === 'brain' || path === '/brain' || path.endsWith('/brain');
}

// SPA-smooth return to the main app, from either a hash or a path entry.
function goHome(): void {
  const path = window.location.pathname.replace(/\/+$/, '').toLowerCase();
  if (path === '/brain' || path.endsWith('/brain')) {
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
  useEffect(() => {
    const onChange = () => setBrain(isBrainRoute());
    window.addEventListener('hashchange', onChange);
    window.addEventListener('popstate', onChange);
    return () => {
      window.removeEventListener('hashchange', onChange);
      window.removeEventListener('popstate', onChange);
    };
  }, []);

  if (!brain) return <App />;
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
