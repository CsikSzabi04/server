import { useCallback, useRef, useState } from 'react';
import HudBackground from './components/HudBackground';
import ScanlineOverlay from './components/ScanlineOverlay';
import MindCore from './components/MindCore';
import Residents from './components/Residents';
import CornerHud from './components/CornerHud';
import ChatPanel from './components/ChatPanel';
import InputBar from './components/InputBar';
import SideWidgets from './components/SideWidgets';
import SoundToggle from './components/SoundToggle';
import VoiceToggle from './components/VoiceToggle';
import type { AuriState } from './lib/auriState';
import { type ChatMessage, getEndpointLabel, getMode, streamChat } from './lib/api';
import { blip } from './lib/sound';
import { cancel as voiceCancel, feed as voiceFeed, flush as voiceFlush } from './lib/voice';
import type { UIMessage } from './types';

let idCounter = 0;
const newId = () => `m${++idCounter}`;

const GREETING =
  'Rendszer online. Auri készenlétben — kérdezz bármit. (Ez most DEMO mód; a valódi modell bekötése a README-ben.)';

export default function App() {
  const [messages, setMessages] = useState<UIMessage[]>([
    { id: newId(), role: 'assistant', content: GREETING },
  ]);
  const [state, setState] = useState<AuriState>('idle');
  const [totalTokens, setTotalTokens] = useState(0);
  const [latency, setLatency] = useState(0);
  const [residentsOn, setResidentsOn] = useState(true);
  const [core3D, setCore3D] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  const busy = state === 'thinking' || state === 'speaking';

  const send = useCallback(
    (text: string) => {
      if (!text.trim() || busy) return;
      blip('send');
      voiceCancel(); // stop any in-progress speech before a new turn

      const userMsg: UIMessage = { id: newId(), role: 'user', content: text };
      const auriId = newId();
      const history: ChatMessage[] = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      setMessages((prev) => [...prev, userMsg]);
      setState('thinking');

      const ctrl = new AbortController();
      abortRef.current = ctrl;
      let created = false;

      void streamChat(
        history,
        {
          onDelta: (delta) => {
            voiceFeed(delta); // speak sentence-by-sentence as it streams
            if (!created) {
              created = true;
              setState('speaking');
              blip('recv');
              setMessages((prev) => [
                ...prev,
                { id: auriId, role: 'assistant', content: delta, streaming: true },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((m) => (m.id === auriId ? { ...m, content: m.content + delta } : m)),
              );
            }
          },
          onDone: ({ usage, latencyMs }) => {
            voiceFlush(); // speak any trailing partial sentence
            setMessages((prev) => prev.map((m) => (m.id === auriId ? { ...m, streaming: false } : m)));
            if (usage) setTotalTokens((t) => t + usage.total_tokens);
            setLatency(latencyMs);
            setState('idle');
          },
          onError: (msg) => {
            blip('error');
            voiceCancel();
            setMessages((prev) =>
              created
                ? prev.map((m) =>
                    m.id === auriId
                      ? { ...m, content: `${m.content}\n\n${msg}`, streaming: false, error: true }
                      : m,
                  )
                : [...prev, { id: auriId, role: 'assistant', content: msg, error: true }],
            );
            setState('error');
            window.setTimeout(() => setState((s) => (s === 'error' ? 'idle' : s)), 2800);
          },
        },
        ctrl.signal,
      );
    },
    [messages, busy],
  );

  const onTypingChange = useCallback((typing: boolean) => {
    setState((s) => (s === 'idle' || s === 'listening' ? (typing ? 'listening' : 'idle') : s));
  }, []);

  const intensity =
    state === 'thinking' ? 2.4 : state === 'speaking' ? 1.8 : state === 'listening' ? 1.4 : 1;

  return (
    <div className="hud-root" data-state={state}>
      <HudBackground intensity={intensity} />
      <div className="hud-grid" aria-hidden="true" />
      <ScanlineOverlay />
      <CornerHud state={state} mode={getEndpointLabel()} />

      <header className="hud-header">
        <div className="brand">
          <span className="brand-mark">◈</span>
          <span className="brand-name">
            AURI<span className="brand-sub">GPT</span>
          </span>
        </div>
        <div className="brand-status" data-state={state}>
          {getMode() === 'mock' ? 'DEMO // MOCK CORE' : `LIVE LINK // ${getEndpointLabel()}`}
        </div>
        <div className="hud-toggles">
          <button
            className="sound-toggle"
            onClick={() => setCore3D((v) => !v)}
            aria-pressed={core3D}
            title="3D mag ki/be (teljesítmény)"
          >
            <span aria-hidden="true">◉</span>
            <span>{core3D ? '3D' : '2D'}</span>
          </button>
          <SoundToggle />
          <VoiceToggle />
          <button
            className="sound-toggle"
            onClick={() => setResidentsOn((v) => !v)}
            aria-pressed={residentsOn}
            title="Pixel-lakók ki/be"
          >
            <span aria-hidden="true">👾</span>
            <span>{residentsOn ? 'LAKÓK' : 'OFF'}</span>
          </button>
        </div>
      </header>

      <main className="hud-main">
        <section className="reactor-stage">
          <MindCore state={state} force2D={!core3D} />
        </section>

        <section className="chat-stage">
          <ChatPanel messages={messages} thinking={state === 'thinking'} />
          <InputBar disabled={busy} onSend={send} onTypingChange={onTypingChange} />
        </section>

        <SideWidgets
          tokens={totalTokens}
          latencyMs={latency}
          speaking={state === 'speaking'}
          mode={getEndpointLabel()}
        />
      </main>

      <Residents state={state} enabled={residentsOn} />
    </div>
  );
}
