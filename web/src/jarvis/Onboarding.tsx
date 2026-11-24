// AI-3 (BODY) — the 4 onboarding questions as a form (spec 5.11), shown only when signed in.
// Auri asks the same questions by voice (AI-2); answering here or by voice is equivalent:
// every card saves just its own key (`prefs.set` {key, answered:[key]}), and the daemon marks
// `onboarded` once all four are answered. The card Auri is asking right now is highlighted.
import { type ReactNode, useEffect, useState } from 'react';
import type { DaemonEvents, HudCommandType, HudCommands, JarvisPrefs, PrefKey, RoutineApp, RoutineUrl, VoiceName, WakeWord } from './protocol';

interface Props {
  prefs: JarvisPrefs;
  options: DaemonEvents['options'];
  step: number | null;
  send: <K extends HudCommandType>(type: K, data: HudCommands[K]) => boolean;
  onClose: () => void;
}

const VOICES: { id: VoiceName; label: string; hint: string }[] = [
  { id: 'daniel', label: 'Daniel', hint: 'brit, mély (ElevenLabs)' },
  { id: 'george', label: 'George', hint: 'brit, meleg (ElevenLabs)' },
  { id: 'piper', label: 'Csak helyi', hint: 'Piper — offline, ingyen' },
];
const WAKES: { id: WakeWord; label: string }[] = [
  { id: 'hey_auri', label: '„Hey Auri”' },
  { id: 'hey_jarvis', label: '„Hey Jarvis”' },
];
const STEP_KEY: Record<number, PrefKey> = { 1: 'address', 2: 'wake_word', 3: 'voice', 4: 'welcome_routine' };

function isHttp(u: string) {
  return /^https?:\/\/\S+$/i.test(u.trim());
}

export default function Onboarding({ prefs, options, step, send, onClose }: Props) {
  const [address, setAddress] = useState(prefs.address === 'you' ? '' : prefs.address);
  const [wake, setWake] = useState<WakeWord>(prefs.wake_word);
  const [voice, setVoice] = useState<VoiceName>(prefs.voice);
  const [wantRoutine, setWantRoutine] = useState(prefs.welcome_routine !== null);
  const [music, setMusic] = useState(prefs.welcome_routine?.music_url ?? '');
  const [apps, setApps] = useState<RoutineApp[]>(prefs.welcome_routine?.apps ?? []);
  const [urls, setUrls] = useState<RoutineUrl[]>(prefs.welcome_routine?.urls ?? []);
  const [err, setErr] = useState<string | null>(null);

  // follow changes made by voice while the form is open
  useEffect(() => setWake(prefs.wake_word), [prefs.wake_word]);
  useEffect(() => setVoice(prefs.voice), [prefs.voice]);

  const answered = new Set(prefs.answered);
  const active = step ? STEP_KEY[step] : null;
  const monitorCount = Math.max(1, Math.min(3, options.monitors.length || 3)) as 1 | 2 | 3;
  const monitors = [1, 2, 3].slice(0, monitorCount) as (1 | 2 | 3)[];

  const save = (key: PrefKey, data: Partial<JarvisPrefs>) => {
    setErr(null);
    if (!send('prefs.set', { ...data, answered: [key] })) setErr('Nincs kapcsolat a daemonnal.');
  };

  const saveRoutine = () => {
    if (!wantRoutine) return save('welcome_routine', { welcome_routine: null });
    const m = music.trim();
    if (m && !isHttp(m) && !/^spotify:\S+$/i.test(m)) return setErr('A zene http(s) vagy spotify: cím legyen.');
    const badUrl = urls.find((u) => !isHttp(u.url));
    if (badUrl) return setErr(`Hibás URL: ${badUrl.url || '(üres)'}`);
    save('welcome_routine', { welcome_routine: { music_url: m || null, apps, urls } });
  };

  const card = (key: PrefKey, n: number, title: string, body: ReactNode) => (
    <section className={`jv-card${active === key ? ' is-active' : ''}${answered.has(key) ? ' is-done' : ''}`}>
      <header>
        <span className="jv-card-n">{answered.has(key) ? '✓' : n}</span>
        <h3>{title}</h3>
      </header>
      {body}
    </section>
  );

  return (
    <div className="jv-onboarding" role="dialog" aria-label="Beállítás">
      <div className="jv-onboarding-head">
        <h2>Ismerkedjünk meg</h2>
        <p>Auri hangosan is kérdez — válaszolhatsz itt vagy szóban, mindegy.</p>
        <button className="jv-btn ghost" onClick={onClose} aria-label="Bezárás">
          ✕
        </button>
      </div>

      {card(
        'address',
        1,
        'Hogyan szólítsalak?',
        <div className="jv-row">
          <input
            className="jv-input"
            value={address}
            maxLength={40}
            placeholder="pl. Szabi, uram — vagy hagyd üresen"
            onChange={(e) => setAddress(e.target.value)}
          />
          <button className="jv-btn" onClick={() => save('address', { address: address.trim() || 'you' })}>
            Mentés
          </button>
        </div>,
      )}

      {card(
        'wake_word',
        2,
        'Melyik ébresztőszó?',
        <div className="jv-row">
          {WAKES.map((w) => (
            <button
              key={w.id}
              className={`jv-chip${wake === w.id ? ' on' : ''}`}
              onClick={() => {
                setWake(w.id);
                save('wake_word', { wake_word: w.id });
              }}
            >
              {w.label}
            </button>
          ))}
        </div>,
      )}

      {card(
        'voice',
        3,
        'Melyik hang tetszik?',
        <div className="jv-voices">
          {VOICES.map((v) => (
            <div key={v.id} className={`jv-voice${voice === v.id ? ' on' : ''}`}>
              <button className="jv-chip-plain" onClick={() => setVoice(v.id)}>
                <b>{v.label}</b>
                <small>{v.hint}</small>
              </button>
              <button className="jv-btn ghost" title="Minta lejátszása" onClick={() => send('voice.sample', { voice: v.id })}>
                ▶ minta
              </button>
            </div>
          ))}
          <button className="jv-btn" onClick={() => save('voice', { voice })}>
            Ezt kérem
          </button>
        </div>,
      )}

      {card(
        'welcome_routine',
        4,
        'Kérsz „Üdv itthon” rutint?',
        <div className="jv-routine">
          <div className="jv-row">
            <button className={`jv-chip${wantRoutine ? ' on' : ''}`} onClick={() => setWantRoutine(true)}>
              Igen
            </button>
            <button className={`jv-chip${!wantRoutine ? ' on' : ''}`} onClick={() => setWantRoutine(false)}>
              Nem
            </button>
          </div>
          {wantRoutine && (
            <>
              <label className="jv-label">
                Zene (YouTube / Spotify link)
                <input className="jv-input" value={music} placeholder="https://… vagy spotify:…" onChange={(e) => setMusic(e.target.value)} />
              </label>
              <div className="jv-label">Appok</div>
              {apps.map((a, i) => (
                <div key={i} className="jv-row">
                  <select
                    className="jv-input"
                    value={a.app}
                    onChange={(e) => setApps(apps.map((x, j) => (j === i ? { ...x, app: e.target.value } : x)))}
                  >
                    {options.apps.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                  <select
                    className="jv-input narrow"
                    value={a.monitor}
                    onChange={(e) => setApps(apps.map((x, j) => (j === i ? { ...x, monitor: Number(e.target.value) as 1 | 2 | 3 } : x)))}
                  >
                    {monitors.map((n) => (
                      <option key={n} value={n}>
                        {n}. monitor
                      </option>
                    ))}
                  </select>
                  <label className="jv-check">
                    <input
                      type="checkbox"
                      checked={a.fullscreen}
                      onChange={(e) => setApps(apps.map((x, j) => (j === i ? { ...x, fullscreen: e.target.checked } : x)))}
                    />
                    teljes
                  </label>
                  <button className="jv-btn ghost" onClick={() => setApps(apps.filter((_, j) => j !== i))}>
                    ✕
                  </button>
                </div>
              ))}
              {apps.length < 8 && options.apps.length > 0 && (
                <button className="jv-btn ghost" onClick={() => setApps([...apps, { app: options.apps[0].id, monitor: 2, fullscreen: false }])}>
                  + app
                </button>
              )}
              {options.apps.length === 0 && <p className="jv-muted">Az app-lista (apps.yaml) még üres.</p>}
              <div className="jv-label">Weboldalak</div>
              {urls.map((u, i) => (
                <div key={i} className="jv-row">
                  <input
                    className="jv-input"
                    value={u.url}
                    placeholder="https://…"
                    onChange={(e) => setUrls(urls.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))}
                  />
                  <select
                    className="jv-input narrow"
                    value={u.monitor}
                    onChange={(e) => setUrls(urls.map((x, j) => (j === i ? { ...x, monitor: Number(e.target.value) as 1 | 2 | 3 } : x)))}
                  >
                    {monitors.map((n) => (
                      <option key={n} value={n}>
                        {n}. monitor
                      </option>
                    ))}
                  </select>
                  <button className="jv-btn ghost" onClick={() => setUrls(urls.filter((_, j) => j !== i))}>
                    ✕
                  </button>
                </div>
              ))}
              {urls.length < 8 && (
                <button className="jv-btn ghost" onClick={() => setUrls([...urls, { url: '', monitor: 1 }])}>
                  + weboldal
                </button>
              )}
            </>
          )}
          <button className="jv-btn" onClick={saveRoutine}>
            Mentés
          </button>
        </div>,
      )}

      {err && <p className="jv-error">{err}</p>}
      {prefs.onboarded && (
        <p className="jv-ok">
          ✓ Minden beállítva.{' '}
          <button className="jv-btn" onClick={onClose}>
            Kész
          </button>
        </p>
      )}
    </div>
  );
}
