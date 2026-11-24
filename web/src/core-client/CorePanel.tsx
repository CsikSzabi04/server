// CorePanel — the /brain page's switch for the local Auri Core (owner: AI-3, P1; spec 01/03 §7.3–7.4).
// Switch (`auri.brain.core`, default off) · token (once, from auri-core/data/core.token) · status ·
// one-off import of the signed-in user's old brain_state into their own T1 (as hypotheses).

import { useCallback, useEffect, useState } from 'react';
import { brainStore } from '../brain/brainStore';
import { supabase } from '../lib/supabase';
import {
  CORE_TOKEN_KEY,
  coreHealth,
  coreImportBrainState,
  isCoreEnabled,
  setCoreEnabled,
  type CoreHealth,
} from './coreClient';

type Status = { kind: 'off' } | { kind: 'checking' } | { kind: 'down' } | { kind: 'up'; health: CoreHealth };

function hasToken(): boolean {
  try {
    return Boolean(import.meta.env.VITE_AURI_CORE_TOKEN || localStorage.getItem(CORE_TOKEN_KEY));
  } catch {
    return false;
  }
}

export default function CorePanel() {
  const [on, setOn] = useState(isCoreEnabled());
  const [status, setStatus] = useState<Status>({ kind: on ? 'checking' : 'off' });
  const [tokenSet, setTokenSet] = useState(hasToken());
  const [tokenInput, setTokenInput] = useState('');
  const [note, setNote] = useState('');

  const refresh = useCallback(async () => {
    if (!isCoreEnabled()) return setStatus({ kind: 'off' });
    setStatus({ kind: 'checking' });
    const h = await coreHealth();
    setStatus(h?.ok ? { kind: 'up', health: h } : { kind: 'down' });
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, on, tokenSet]);

  const toggle = () => {
    setCoreEnabled(!on);
    setOn(!on);
    setNote('');
  };

  const saveToken = () => {
    const t = tokenInput.trim();
    if (t.length < 32) return setNote('A token túl rövid — másold be az auri-core/data/core.token tartalmát.');
    try {
      localStorage.setItem(CORE_TOKEN_KEY, t);
      setTokenSet(true);
      setTokenInput('');
      setNote('Token elmentve ebben a böngészőben.');
    } catch {
      setNote('A böngésző nem engedi a mentést.');
    }
  };

  const importOld = async () => {
    setNote('Importálás…');
    const { data } = (await supabase?.auth.getSession()) ?? { data: { session: null } };
    const userId = data.session?.user.id ?? null;
    if (!userId) return setNote('Az importhoz jelentkezz be — vendégként a Core semmit nem tárol.');
    const state = await brainStore.exportJSON(userId);
    if (!state?.qa?.length) return setNote('A régi agyban nincs kérdés–válasz pár, nincs mit átvinni.');
    const r = await coreImportBrainState(state);
    setNote(
      r
        ? `Kész: ${r.added} pár átkerült a saját táradba (feltételezésként), ${r.dropped} személyes adat miatt kimaradt, ${r.skipped} üres/túl hosszú.`
        : 'Az import nem sikerült — fut a Core (auri_core serve)?',
    );
  };

  const label =
    status.kind === 'off'
      ? 'kikapcsolva — a böngészős agy válaszol'
      : status.kind === 'checking'
        ? 'ellenőrzés…'
        : status.kind === 'down'
          ? tokenSet
            ? 'nem elérhető — indítsd el: auri-core\\.venv\\Scripts\\python -m auri_core serve'
            : 'token kell (auri-core/data/core.token)'
          : `fut · ${status.health.ollama.loaded.join(', ') || 'nincs betöltött modell'}${status.health.lane.busy ? ' · a modell foglalt' : ''}`;

  return (
    <section className="bx-core" style={{ marginTop: 12 }} title="Auri Core — a helyi gondolkodó agy (127.0.0.1:8791)">
      <h4>
        Auri Core <span>{label}</span>
      </h4>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
        <input type="checkbox" checked={on} onChange={toggle} />
        a Core válaszoljon, ha fut
      </label>
      {on && !tokenSet && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <input
            type="password"
            placeholder="core.token"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            autoComplete="off"
            style={{ flex: 1, minWidth: 0 }}
          />
          <button type="button" onClick={saveToken}>
            mentés
          </button>
        </div>
      )}
      {status.kind === 'up' && (
        <button type="button" onClick={() => void importOld()} style={{ marginTop: 8 }}>
          régi agy importja a saját tárba
        </button>
      )}
      {note && <p style={{ marginTop: 6, opacity: 0.8 }}>{note}</p>}
    </section>
  );
}
