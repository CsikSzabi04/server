import { useState } from 'react';
import { createPortal } from 'react-dom';
import type { AuthApi } from '../hooks/useAuth';

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

  if (!auth.configured) return null;

  if (auth.user) {
    return (
      <button
        className="sound-toggle"
        onClick={() => void auth.signOut()}
        title={`Kilépés (${auth.user.email ?? ''})`}
      >
        <span aria-hidden="true">⏻</span>
        <span>KILÉP</span>
      </button>
    );
  }

  const submit = async () => {
    if (!email || !password) {
      setErr('Add meg az e-mailt és a jelszót.');
      return;
    }
    setBusy(true);
    setErr(null);
    setInfo(null);
    const e = mode === 'in' ? await auth.signIn(email, password) : await auth.signUp(email, password);
    setBusy(false);
    if (e) {
      setErr(e);
    } else if (mode === 'up') {
      setInfo('Fiók létrehozva. Ha kéri, erősítsd meg az e-mailben kapott linket, majd lépj be.');
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
        <div className="auth-title">{mode === 'in' ? 'BEJELENTKEZÉS' : 'REGISZTRÁCIÓ'}</div>
        <input
          className="auth-input"
          type="email"
          placeholder="e-mail"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="auth-input"
          type="password"
          placeholder="jelszó (min. 6 karakter)"
          autoComplete={mode === 'in' ? 'current-password' : 'new-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void submit()}
        />
        {err && <div className="auth-err">{err}</div>}
        {info && <div className="auth-info">{info}</div>}
        <button className="auth-submit" disabled={busy} onClick={() => void submit()}>
          {busy ? '…' : mode === 'in' ? 'Belépés' : 'Fiók létrehozása'}
        </button>
        <button
          className="auth-switch"
          onClick={() => {
            setMode(mode === 'in' ? 'up' : 'in');
            setErr(null);
            setInfo(null);
          }}
        >
          {mode === 'in' ? 'Nincs fiókod? Regisztrálj' : 'Van fiókod? Lépj be'}
        </button>
        <button className="auth-close" onClick={() => setOpen(false)} aria-label="Bezárás">
          ✕
        </button>
      </div>
    </div>
  );

  return (
    <>
      <button className="sound-toggle" onClick={() => setOpen(true)} title="Bejelentkezés / Regisztráció">
        <span aria-hidden="true">👤</span>
        <span>BELÉP</span>
      </button>
      {open && createPortal(modal, document.body)}
    </>
  );
}
