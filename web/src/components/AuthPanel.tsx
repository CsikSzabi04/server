import { useState } from 'react';
import { createPortal } from 'react-dom';
import type { AuthApi } from '../hooks/useAuth';

// Bump when /feltetelek.html or /adatvedelem.html changes materially (their "Hatályos" date).
const TERMS_VERSION = '2026-11-20';

// Login / signup button + modal. Hidden entirely if Supabase isn't configured.
// The modal is rendered via a portal to <body> so the HUD's stacking contexts
// can't cover it (otherwise the chat panel sits on top and steals clicks).
export default function AuthPanel({ auth }: { auth: AuthApi }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);
  // Sign-up consent: 18+ (model providers' terms) + terms & privacy notice (SECURITY.md §20, H-14).
  const [consent, setConsent] = useState(false);

  if (!auth.configured) return null;

  if (auth.user) {
    return (
      <button
        className="sound-toggle"
        onClick={() => void auth.signOut()}
        title={`Sign out (${auth.user.email ?? ''})`}
      >
        <span aria-hidden="true">⏻</span>
        <span>OUT</span>
      </button>
    );
  }

  const submit = async () => {
    if (!email || !password) {
      setErr('Enter your email and password.');
      return;
    }
    if (mode === 'up' && password.length < 10) {
      setErr('Use a password of at least 10 characters.');
      return;
    }
    if (mode === 'up' && !consent) {
      setErr('Please confirm you are 18+ and accept the terms and the privacy notice.');
      return;
    }
    setBusy(true);
    setErr(null);
    setInfo(null);
    // Accountability (GDPR art. 5(2)): keep WHICH terms version was accepted, and WHEN.
    const consentRecord = {
      terms_version: TERMS_VERSION,
      terms_accepted_at: new Date().toISOString(),
      age_confirmed_18_plus: true,
    };
    const e = mode === 'in' ? await auth.signIn(email, password) : await auth.signUp(email, password, consentRecord);
    setBusy(false);
    if (e) {
      setErr(e);
    } else if (mode === 'up') {
      setInfo('Account created. If prompted, confirm the link sent to your email, then sign in.');
      setMode('in');
    } else {
      setOpen(false);
      setEmail('');
      setPassword('');
    }
  };

  const modal = (
    <div className="auth-overlay" onClick={() => setOpen(false)}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="auth-title">{mode === 'in' ? 'SIGN IN' : 'SIGN UP'}</div>
        <input
          className="auth-input"
          type="email"
          placeholder="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="auth-input"
          type="password"
          placeholder={mode === 'in' ? 'password' : 'password (min. 10 characters)'}
          autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void submit()}
        />
        {mode === 'up' && (
          <label className="auth-consent">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              Elmúltam 18 éves, és elfogadom a{' '}
              <a href="/feltetelek.html" target="_blank" rel="noopener">
                felhasználási feltételeket
              </a>{' '}
              és az{' '}
              <a href="/adatvedelem.html" target="_blank" rel="noopener">
                adatkezelési tájékoztatót
              </a>
              .
            </span>
          </label>
        )}
        {err && <div className="auth-err">{err}</div>}
        {info && <div className="auth-info">{info}</div>}
        <button className="auth-submit" disabled={busy} onClick={() => void submit()}>
          {busy ? '…' : mode === 'in' ? 'Sign in' : 'Create account'}
        </button>
        <button
          className="auth-switch"
          onClick={() => {
            setMode(mode === 'in' ? 'up' : 'in');
            setErr(null);
            setInfo(null);
          }}
        >
          {mode === 'in' ? 'No account? Sign up' : 'Have an account? Sign in'}
        </button>
        <button className="auth-close" onClick={() => setOpen(false)} aria-label="Close">
          ✕
        </button>
      </div>
    </div>
  );

  return (
    <>
      <button className="sound-toggle" onClick={() => setOpen(true)} title="Sign in / Sign up">
        <span aria-hidden="true">👤</span>
        <span>IN</span>
      </button>
      {open && createPortal(modal, document.body)}
    </>
  );
}
