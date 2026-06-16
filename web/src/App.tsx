import { useCallback, useEffect, useRef, useState } from 'react';
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
import AuthPanel from './components/AuthPanel';
import ConversationSidebar from './components/ConversationSidebar';
import BrainCard from './components/BrainCard';
import MemoryView from './components/MemoryView';
import { useAuth } from './hooks/useAuth';
import { useMemory } from './hooks/useMemory';
import type { AuriState } from './lib/auriState';
import { type ChatMessage, getEndpointLabel, getMode, streamChat } from './lib/api';
import { blip } from './lib/sound';
import { cancel as voiceCancel, feed as voiceFeed, flush as voiceFlush } from './lib/voice';
import {
  type ConversationMeta,
  createConversation,
  deleteConversation,
  listConversations,
  loadConversation,
  renameConversation,
  saveMessage,
  setPinned,
} from './lib/chatStore';
import type { UIMessage } from './types';

let idCounter = 0;
const newId = () => `m${++idCounter}`;

const GREETING =
  'Rendszer online. Auri készenlétben — kérdezz bármit. (Ez most DEMO mód; a valódi modell bekötése a README-ben.)';

const greetingMessages = (): UIMessage[] => [{ id: newId(), role: 'assistant', content: GREETING }];

export default function App() {
  const [messages, setMessages] = useState<UIMessage[]>(greetingMessages);
  const [state, setState] = useState<AuriState>('idle');
  const [totalTokens, setTotalTokens] = useState(0);
  const [latency, setLatency] = useState(0);
  const [residentsOn, setResidentsOn] = useState(true);
  const [core3D, setCore3D] = useState(true);
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [brainHover, setBrainHover] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const convIdRef = useRef<string | null>(null);

  const auth = useAuth();
  const memory = useMemory(auth.user?.id ?? null);

  const setConv = useCallback((id: string | null) => {
    convIdRef.current = id;
    setCurrentConvId(id);
  }, []);

  const refreshConversations = useCallback(async () => {
    setConversations(await listConversations(auth.user?.id ?? null));
  }, [auth.user?.id]);

  // On mount / login change: load the conversation list + restore the latest one.
  useEffect(() => {
    const uid = auth.user?.id ?? null;
    let cancelled = false;
    void (async () => {
      const list = await listConversations(uid);
      if (cancelled) return;
      setConversations(list);
      if (list.length) {
        const msgs = await loadConversation(uid, list[0].id);
        if (cancelled) return;
        setConv(list[0].id);
        setMessages(msgs.length ? msgs.map((m) => ({ id: newId(), role: m.role, content: m.content })) : greetingMessages());
      } else {
        setConv(null);
        setMessages(greetingMessages());
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth.user?.id, setConv]);

  const busy = state === 'thinking' || state === 'speaking';

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    voiceCancel();
    setConv(null);
    setMessages(greetingMessages());
    setArchiveOpen(false);
    blip('recv');
    // little "reboot" pulse on the core
    setState('thinking');
    window.setTimeout(() => setState((s) => (s === 'thinking' ? 'idle' : s)), 600);
  }, [setConv]);

  const openConversation = useCallback(
    async (id: string) => {
      abortRef.current?.abort();
      voiceCancel();
      const msgs = await loadConversation(auth.user?.id ?? null, id);
      setConv(id);
      setMessages(msgs.length ? msgs.map((m) => ({ id: newId(), role: m.role, content: m.content })) : greetingMessages());
      setArchiveOpen(false);
    },
    [auth.user?.id, setConv],
  );

  const onRename = useCallback(
    async (id: string, title: string) => {
      await renameConversation(auth.user?.id ?? null, id, title);
      void refreshConversations();
    },
    [auth.user?.id, refreshConversations],
  );

  const onDelete = useCallback(
    async (id: string) => {
      await deleteConversation(auth.user?.id ?? null, id);
      if (convIdRef.current === id) newChat();
      void refreshConversations();
    },
    [auth.user?.id, refreshConversations, newChat],
  );

  const onPin = useCallback(
    async (id: string, pinned: boolean) => {
      await setPinned(auth.user?.id ?? null, id, pinned);
      void refreshConversations();
    },
    [auth.user?.id, refreshConversations],
  );

  const send = useCallback(
    (text: string) => {
      if (!text.trim() || busy) return;
      blip('send');
      voiceCancel();

      const uid = auth.user?.id ?? null;
      const userMsg: UIMessage = { id: newId(), role: 'user', content: text };
      const auriId = newId();
      // Inject the BRAIN: persona + what Auri remembers that's relevant now.
      const history: ChatMessage[] = [
        { role: 'system', content: memory.systemMessage(text) },
        ...[...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
      ];

      setMessages((prev) => [...prev, userMsg]);
      setState('thinking');

      // Persist (everyone): ensure a conversation, save the user message.
      void (async () => {
        if (!convIdRef.current) {
          const cid = await createConversation(uid, text);
          if (cid) setConv(cid);
        }
        if (convIdRef.current) await saveMessage(uid, convIdRef.current, 'user', text);
        void refreshConversations();
      })();

      const ctrl = new AbortController();
      abortRef.current = ctrl;
      let created = false;
      let assistantText = '';

      void streamChat(
        history,
        {
          onDelta: (delta) => {
            assistantText += delta;
            voiceFeed(delta);
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
            voiceFlush();
            setMessages((prev) => prev.map((m) => (m.id === auriId ? { ...m, streaming: false } : m)));
            if (usage) setTotalTokens((t) => t + usage.total_tokens);
            setLatency(latencyMs);
            setState('idle');
            if (convIdRef.current && assistantText.trim()) {
              void saveMessage(uid, convIdRef.current, 'assistant', assistantText).then(() =>
                refreshConversations(),
              );
            }
            if (assistantText.trim()) void memory.ingest(text, assistantText);
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
    [messages, busy, auth.user, memory, setConv, refreshConversations],
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

      <ConversationSidebar
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        conversations={conversations}
        currentId={currentConvId}
        onNew={newChat}
        onOpen={openConversation}
        onRename={onRename}
        onDelete={onDelete}
        onPin={onPin}
      />

      <header className="hud-header">
        <div className="brand">
          <button
            className="archive-toggle"
            onClick={() => setArchiveOpen((v) => !v)}
            aria-pressed={archiveOpen}
            title="Előzmények"
          >
            ☰
          </button>
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
            onClick={newChat}
            title="Új beszélgetés"
          >
            <span aria-hidden="true">＋</span>
            <span>ÚJ</span>
          </button>
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
          <AuthPanel auth={auth} />
        </div>
      </header>

      <main className="hud-main">
        <section
          className="reactor-stage brain-host"
          onMouseEnter={() => setBrainHover(true)}
          onMouseLeave={() => setBrainHover(false)}
        >
          <MindCore state={state} force2D={!core3D} />
          <div className="brain-hint" aria-hidden="true">
            BRAIN ●
          </div>
          {brainHover && (
            <BrainCard
              memory={memory}
              conversationCount={conversations.length}
              onOpen={() => {
                setMemoryOpen(true);
                setBrainHover(false);
              }}
            />
          )}
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

      {memoryOpen && <MemoryView memory={memory} onClose={() => setMemoryOpen(false)} />}
    </div>
  );
}
