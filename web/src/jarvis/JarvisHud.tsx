// AI-3 (BODY) — /jarvis: the live HUD of the local Jarvis daemon (spec 5.9) — the desktop app.
// Same look as AuriGPT: the MindCore (3D golden mind inside the reactor rings, pulsing on the
// mic / output level), the ARCHIVE sidebar (CODE · BRAIN · NEW CHAT · search · history — Jarvis
// conversations are saved there when signed in) and the /brain page. Plus: live chat
// (transcripts + streamed replies), tool log, latency bar, system stats, command box,
// telemetry strip (UPTIME · TOKENS · LATENCY · CORE LOAD · RIG · VOX, top-left),
// push-to-talk, mute, stop, guest badge + login, onboarding form, proposals, credit meter.
import { type FormEvent, Suspense, lazy, useEffect, useState } from 'react';
import AuthPanel from '../components/AuthPanel';
import ChatPanel from '../components/ChatPanel';
import ConversationSidebar from '../components/ConversationSidebar';
import HudBackground from '../components/HudBackground';
import MindCore from '../components/MindCore';
import ScanlineOverlay from '../components/ScanlineOverlay';
import { useAuth } from '../hooks/useAuth';
import type { AuriState } from '../lib/auriState';
import JarvisTelemetry from './JarvisTelemetry';
import Onboarding from './Onboarding';
import type { DaemonState } from './protocol';
import { useAuthBridge } from './useAuthBridge';
import { useJarvisChats } from './useJarvisChats';
import { useJarvisSocket } from './useJarvisSocket';
import './jarvis.css';

const CodeProjects = lazy(() => import('../components/CodeProjects'));

const STATE_LABEL: Record<DaemonState, string> = {
  idle: 'KÉSZENLÉT',
  listening: 'FIGYELEK',
  transcribing: 'LEÍRÁS',
  thinking: 'GONDOLKODOM',
  speaking: 'BESZÉLEK',
  acting: 'CSELEKSZEM',
};

const TO_AURI: Record<DaemonState, AuriState> = {
  idle: 'idle',
  listening: 'listening',
  transcribing: 'thinking',
  thinking: 'thinking',
  speaking: 'speaking',
  acting: 'thinking',
};

const WAKE_LABEL = { hey_auri: '„Hey Auri”', hey_jarvis: '„Hey Jarvis”' } as const;
const VOICE_LABEL = { daniel: 'Daniel', george: 'George', piper: 'Piper (helyi)' } as const;

function ms(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`;
}

export default function JarvisHud({ onExit }: { onExit?: () => void }) {
  const auth = useAuth();
  const link = useJarvisSocket();
  const { model, status, send } = link;
  const { saveState } = useAuthBridge(auth, link);
  const chats = useJarvisChats(auth, link);
  const [cmd, setCmd] = useState('');
  const [showSetup, setShowSetup] = useState(false);
  const [tokenDraft, setTokenDraft] = useState('');
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [codeOpen, setCodeOpen] = useState(false);
  // phone / narrow window: the core view (telemetry + reactor) first; once a conversation
  // exists the chat takes the whole page — ◉ goes back to the core, a new message returns.
  const [showCore, setShowCore] = useState(false);
  const chatLen = model.chat.length;
  const chatMode = chatLen > 0 && !showCore;
  useEffect(() => {
    if (chatLen > 0) setShowCore(false);
  }, [chatLen]);

  const connected = status === 'open';
  const isUser = model.identity.tier === 'user';
  const prefs = model.identity.prefs;
  const needsOnboarding = isUser && !prefs.onboarded;
  const auriState: AuriState = connected ? TO_AURI[model.state] : 'error';
  const level = model.state === 'speaking' ? model.out : model.state === 'listening' ? model.mic : 0;
  const pulse = 1 + Math.min(level * 3, 0.22);
  const last = model.timings[model.timings.length - 1];

  useEffect(() => {
    document.title = 'Auri // J.A.R.V.I.S.';
  }, []);

  // open the form automatically for a first login (or when Auri starts asking)
  useEffect(() => {
    if (needsOnboarding) setShowSetup(true);
  }, [needsOnboarding]);
  useEffect(() => {
    if (!isUser) setShowSetup(false);
  }, [isUser]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = cmd.trim();
    if (text && send('command', { text })) {
      link.local({ type: 'local.userText', text });
      setCmd('');
    }
  };

  const tr = model.transcript;
  const transcriptDiffers = !!tr && tr.raw.trim() !== tr.text.trim();
  const thinking = connected && (model.state === 'thinking' || model.state === 'transcribing' || model.state === 'acting');

  return (
    <div className={`jv-root state-${connected ? model.state : 'offline'}${chatMode ? ' jv-chatmode' : ''}`}>
      <div className="jv-bg" aria-hidden="true">
        <HudBackground intensity={model.state === 'idle' ? 1 : 1.8} />
        <ScanlineOverlay />
      </div>

      <header className="jv-top">
        <div className="jv-brand">
          <button
            className="jv-btn ghost jv-archive-btn"
            onClick={() => {
              chats.refresh();
              setArchiveOpen((v) => !v);
            }}
            aria-pressed={archiveOpen}
            title="Előzmények (ARCHIVE)"
          >
            ☰
          </button>
          {onExit && (
            <button className="jv-btn ghost" onClick={onExit} title="Vissza az AuriGPT-be">
              ←
            </button>
          )}
          <span>AURI</span>
          <i>// J.A.R.V.I.S.</i>
        </div>
        <div className="jv-link" title={`Daemon: ${status}`}>
          <span className={`jv-dot ${status}`} />
          {status === 'open' ? 'ONLINE' : status === 'no-token' ? 'NINCS TOKEN' : status === 'connecting' ? 'KAPCSOLÓDÁS…' : 'OFFLINE'}
          {model.version && <small>v{model.version}</small>}
        </div>
        <div className="jv-who">
          {isUser ? (
            <span className="jv-badge user">{model.identity.name || 'Bejelentkezve'}</span>
          ) : (
            <span className="jv-badge guest" title="Vendég: „you” · Hey Auri · Daniel · nincs rutin, nincs személyes adat">
              Vendég mód
            </span>
          )}
          {isUser && (
            <button className="jv-btn ghost" onClick={() => setShowSetup((v) => !v)} title="Beállítás (újra)">
              ⚙
            </button>
          )}
          <AuthPanel auth={auth} />
        </div>
      </header>

      {status === 'no-token' && (
        <div className="jv-token">
          <p>
            Ezt az oldalt a daemon szolgálja ki: <code>http://127.0.0.1:8790/#jarvis</code>. Fejlesztéshez add meg a HUD-tokent
            (a daemon kiírja induláskor):
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              link.setToken(tokenDraft);
            }}
          >
            <input className="jv-input" value={tokenDraft} onChange={(e) => setTokenDraft(e.target.value)} placeholder="token" />
            <button className="jv-btn">OK</button>
          </form>
        </div>
      )}

      <main className="jv-main">
        <div className="jv-left">
          <JarvisTelemetry model={model} connected={connected} />
          <section className="jv-core">
            <div className="jv-reactor" style={{ transform: `scale(${pulse.toFixed(3)})` }}>
              <MindCore state={auriState} />
            </div>
            <button className="jv-brain-link" onClick={() => (window.location.hash = 'brain')} title="A BRAIN 3D neurális térképe">
              BRAIN ●
            </button>
            <div className="jv-state">
              {connected ? STATE_LABEL[model.state] : 'NINCS KAPCSOLAT'}
              {model.followUp && model.state === 'listening' && <small> · folytathatod</small>}
              {model.muted && <small className="jv-muted-tag"> · NÉMÍTVA</small>}
            </div>
            <div className="jv-prefs-line">
              {WAKE_LABEL[prefs.wake_word]} · {VOICE_LABEL[prefs.voice]} · {prefs.address === 'you' || !prefs.address ? '„you”' : prefs.address}
            </div>
            {connected && model.warmup && (model.warmup.mind !== 'ready' || model.warmup.voice !== 'ready') && (
              <div className="jv-warm">
                {model.warmup.mind === 'loading' && <span className="loading">Agy töltődik…</span>}
                {model.warmup.mind === 'error' && <span className="bad">Agy: hiba (Ollama?)</span>}
                {model.warmup.voice === 'loading' && <span className="loading">Hang töltődik…</span>}
                {model.warmup.voice === 'error' && <span className="bad">Hang: hiba</span>}
              </div>
            )}
            <div className="jv-controls">
              <button
                className="jv-btn big"
                disabled={!connected}
                onPointerDown={() => send('ptt', { down: true })}
                onPointerUp={() => send('ptt', { down: false })}
                title="Beszélj (push-to-talk)"
              >
                🎙 Beszélj
              </button>
              <button className={`jv-btn${model.muted ? ' on' : ''}`} disabled={!connected} onClick={() => send('mute', { on: !model.muted })}>
                {model.muted ? '🔇 Némítva' : '🔈 Némítás'}
              </button>
              <button className="jv-btn" disabled={!connected} onClick={() => send('stop', {})}>
                ■ Állj
              </button>
            </div>
            {chatLen > 0 && (
              <button className="jv-btn jv-mobile-only" onClick={() => setShowCore(false)}>
                💬 Vissza a beszélgetéshez
              </button>
            )}
          </section>
        </div>

        <section className="jv-feed">
          <div className="jv-panel grow jv-chat">
            <h4>
              {chatMode && (
                <button
                  className="jv-btn ghost jv-mini-core jv-mobile-only"
                  onClick={() => setShowCore(true)}
                  title="Vissza a reaktorhoz (Beszélj · Némítás · Állj)"
                >
                  ◉
                </button>
              )}
              Beszélgetés
              {model.replyModel && <small> · {model.replyModel}</small>}
              {chats.enabled && <small> · mentve az ARCHIVE-ba</small>}
              <button className="jv-btn ghost jv-mini" onClick={chats.newChat} title="Új beszélgetés">
                + új
              </button>
            </h4>
            {model.chat.length === 0 ? (
              <p className="jv-muted">Mondd: {WAKE_LABEL[prefs.wake_word]}, nyomd a 🎙 gombot, vagy írj lent.</p>
            ) : (
              <div className="jv-chat-body">
                <ChatPanel messages={model.chat} thinking={thinking && !model.chat[model.chat.length - 1]?.streaming} />
              </div>
            )}
            {tr && (
              <p className="jv-meta">
                {tr.engine} · STT {ms(tr.stt_ms)}
                {transcriptDiffers && ` · nyers: „${tr.raw}”`}
                {model.route && ` · ${model.route.path}${model.route.intent ? `: ${model.route.intent}` : ''}`}
              </p>
            )}
          </div>

          <div className={`jv-panel${model.tools.length === 0 ? ' jv-tools-empty' : ''}`}>
            <h4>Eszközök</h4>
            {model.tools.length === 0 ? (
              <p className="jv-muted">Még nem futott eszköz.</p>
            ) : (
              <ul className="jv-tools">
                {[...model.tools].reverse().map((t, i) => (
                  <li key={`${t.t}-${i}`} className={t.status}>
                    <span>{t.status === 'ok' ? '✓' : t.status === 'needs_confirm' ? '?' : '✗'}</span>
                    <b>{t.name}</b>
                    <em>{t.message ?? t.status}</em>
                    <small>{ms(t.ms)}</small>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>

      <footer className="jv-bottom">
        <div className="jv-timing jv-desk-only" title="Az utolsó kör késleltetései">
          <span>STT {ms(last?.stt_ms)}</span>
          <span>LLM {ms(last?.llm_first_ms)}</span>
          <span>TTS {ms(last?.tts_first_ms)}</span>
          <span className="total">∑ {ms(last?.total_ms)}</span>
        </div>
        <div className="jv-stats">
          {model.stats ? (
            <>
              <span className="jv-desk-only">CPU {model.stats.cpu}%</span>
              <span className="jv-desk-only">RAM {model.stats.ram}%</span>
              <span className="ollama">{model.stats.ollama}</span>
            </>
          ) : (
            <span className="jv-muted jv-desk-only">rendszeradatok…</span>
          )}
          {model.credits && (
            <span title={`TTS mód: ${model.credits.mode}`}>
              EL {model.credits.used_month}/{model.credits.budget}
            </span>
          )}
          {isUser && saveState === 'saving' && <span>mentés…</span>}
          {isUser && saveState === 'error' && <span className="jv-err-tag">mentés sikertelen</span>}
        </div>
        <form className="jv-cmd" onSubmit={submit}>
          <input
            className="jv-input"
            value={cmd}
            maxLength={2000}
            placeholder={connected ? 'Írj parancsot… (pl. hány óra van?)' : 'Nincs kapcsolat a daemonnal'}
            disabled={!connected}
            onChange={(e) => setCmd(e.target.value)}
          />
          <button className="jv-btn" disabled={!connected || !cmd.trim()}>
            Küldés
          </button>
        </form>
      </footer>

      {model.errors.length > 0 && (
        <div className="jv-errors">
          {model.errors.slice(-2).map((e, i) => (
            <p key={`${e.t}-${i}`}>
              ⚠ {e.where}: {e.message}
            </p>
          ))}
        </div>
      )}

      {isUser && model.proposals.length > 0 && (
        <div className="jv-proposals">
          {model.proposals.map((p) => (
            <div key={p.id} className="jv-proposal">
              <p>{p.text}</p>
              <button
                className="jv-btn"
                onClick={() => {
                  send('proposal.answer', { id: p.id, accept: true });
                  link.clearProposal(p.id);
                }}
              >
                ✓ Igen
              </button>
              <button
                className="jv-btn ghost"
                onClick={() => {
                  send('proposal.answer', { id: p.id, accept: false });
                  link.clearProposal(p.id);
                }}
              >
                ✕ Nem
              </button>
            </div>
          ))}
        </div>
      )}

      {isUser && showSetup && (
        <Onboarding prefs={prefs} options={model.options} step={model.onboardingStep} send={send} onClose={() => setShowSetup(false)} />
      )}

      {/* the same ARCHIVE sidebar as AuriGPT: CODE · BRAIN · NEW CHAT · search · history */}
      <ConversationSidebar
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        conversations={chats.conversations}
        currentId={chats.currentId}
        onNew={() => {
          chats.newChat();
          setArchiveOpen(false);
        }}
        onOpenCode={() => {
          setCodeOpen(true);
          setArchiveOpen(false);
        }}
        onOpen={(id) => {
          void chats.open(id);
          setArchiveOpen(false);
        }}
        onRename={chats.rename}
        onDelete={chats.remove}
        onPin={chats.pin}
      />
      {codeOpen && (
        <Suspense fallback={null}>
          <CodeProjects onClose={() => setCodeOpen(false)} />
        </Suspense>
      )}
    </div>
  );
}
