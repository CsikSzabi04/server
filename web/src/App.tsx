import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
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
// MemoryView + CodeProjects are heavy modals — lazy-load so they only download when
// opened (smaller startup bundle). Their code.css is eager-imported in main.tsx.
const MemoryView = lazy(() => import('./components/MemoryView'));
const CodeProjects = lazy(() => import('./components/CodeProjects'));
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
import { useBrainChat, localAnswerEnabled, setLocalAnswerEnabled } from './brain-bridge/brainChat';
import { webSearchEnabled, setWebSearchEnabled, searchWeb, searchWebDeep, composeWebAnswer } from './brain-bridge/askPipeline';
import { recordAnswer, alwaysLearn } from './autolearn';

let idCounter = 0;
const newId = () => `m${++idCounter}`;

const GREETING =
  'System online. Auri on standby — ask me anything. (This is DEMO mode; wire up the real model per the README.)';

// Programmer-oriented persona, added to every model request so answers lean technical:
// complete runnable code, exact commands, idiomatic + secure, and the full file(s) when
// asked to build something. (The local brain is already code-first for programming
// questions via recipes/snippets — this steers the model path the same way.)
const PROGRAMMER_SYSTEM =
  'You are Auri, a programming-focused AI assistant. Lean technical and practical. For a code ' +
  'question, give a short explanation then COMPLETE, runnable code (imports, error handling, a brief ' +
  'usage note). Prefer concrete examples, exact install/run commands, and idiomatic, secure code ' +
  'across Python, Node.js, React, JavaScript, TypeScript, Java, SQL, HTML, CSS and Tailwind. When ' +
  'asked to build something (a page, component, API, script), return the full file(s) plus the steps ' +
  "to run it, and cite official docs when useful. For non-code questions, answer helpfully but " +
  "concisely. Reply in the user's language.";

const greetingMessages = (): UIMessage[] => [{ id: newId(), role: 'assistant', content: GREETING }];

export default function App() {
  const [messages, setMessages] = useState<UIMessage[]>(greetingMessages);
  const [state, setState] = useState<AuriState>('idle');
  const [totalTokens, setTotalTokens] = useState(0);
  const [latency, setLatency] = useState(0);
  const [residentsOn, setResidentsOn] = useState(true);
  const [core3D, setCore3D] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [brainHover, setBrainHover] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [codeOpen, setCodeOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const convIdRef = useRef<string | null>(null);

  const auth = useAuth();
  const memory = useMemory(auth.user?.id ?? null);
  // BRAIN (AI-3): feeds the local "literal brain" learner + the opt-in arbiter.
  const brainChat = useBrainChat();
  const [brainOn, setBrainOn] = useState(localAnswerEnabled());
  const [webOn, setWebOn] = useState(webSearchEnabled());

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
      // Inject the BRAIN: persona + what Auri remembers that's relevant now, PLUS the
      // hybrid H1 grounding block (the brain's relevant knowledge) so the model answers
      // grounded in our brain — empty when the brain has nothing relevant.
      const brainCtx = brainChat.groundContext(text, memory.memories);
      const history: ChatMessage[] = [
        { role: 'system', content: memory.systemMessage(text) },
        { role: 'system', content: PROGRAMMER_SYSTEM },
        ...(brainCtx ? [{ role: 'system' as const, content: brainCtx }] : []),
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

      // Render a local/web reply with a word-by-word typewriter (like the model path).
      // The total time is capped (~2.2s) so long code answers still arrive snappily.
      const finishLocal = (content: string, source: 'brain' | 'web') => {
        blip('recv');
        setState('speaking');
        setMessages((prev) => [
          ...prev,
          { id: auriId, role: 'assistant', content: '', streaming: true, source },
        ]);
        const tokens = content.match(/\s+|\S+/g) ?? [content];
        const wordDelay = Math.max(2, Math.min(12, Math.round(2200 / Math.max(1, tokens.length))));
        let acc = '';
        let i = 0;
        const finalize = () => {
          setMessages((prev) =>
            prev.map((m) => (m.id === auriId ? { ...m, content, streaming: false } : m)),
          );
          setState('idle');
          voiceFlush();
          if (convIdRef.current) {
            void saveMessage(uid, convIdRef.current, 'assistant', content).then(() => refreshConversations());
          }
          void memory.ingest(text, content);
          brainChat.observeTurn(text, content);
          recordAnswer(source); // hit-rate metric → /brain "getting smarter" curve
        };
        const tick = () => {
          if (i >= tokens.length) return finalize();
          const tok = tokens[i++];
          acc += tok;
          voiceFeed(tok);
          setMessages((prev) => prev.map((m) => (m.id === auriId ? { ...m, content: acc } : m)));
          window.setTimeout(tick, /^\s+$/.test(tok) ? Math.max(1, wordDelay >> 1) : wordDelay);
        };
        tick();
      };

      // The model path (Ollama → Groq → Gemini), streamed.
      const startModel = () => {
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
                  // 'brain-model' when the brain grounded the model (H1/H3), else plain model.
                  { id: auriId, role: 'assistant', content: delta, streaming: true, source: brainCtx ? 'brain-model' : 'model' },
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
              if (assistantText.trim()) {
                void memory.ingest(text, assistantText);
                brainChat.distill(text, assistantText); // H2: learn the model's answer → offline next time
                recordAnswer('model'); // hit-rate metric → /brain "getting smarter" curve
              }
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
      };

      // Always-learn from the web in the BACKGROUND (opt-in via the 🌐 WEB toggle):
      // every turn searches + feeds the brain so it keeps growing — even when answered
      // from the brain. Fire-and-forget; rate-limited + cached + PII-redacted by AI-4.
      if (webSearchEnabled()) {
        void alwaysLearn(text, { search: searchWeb, ingest: brainChat.learnWebHits });
      }

      // 1) BRAIN first — offline, key-free.
      const brainReply = brainChat.localAnswer(text, memory.memories);
      if (brainReply) {
        finishLocal(brainReply, 'brain');
        return;
      }

      // 2) WEB search (opt-in) when the brain has nothing to say.
      if (webSearchEnabled()) {
        void (async () => {
          const { hits, pages } = await searchWebDeep(text); // deep: also fetch page text
          if (hits.length) {
            brainChat.learnWebHits(text, hits, pages); // store web knowledge + page essence
            finishLocal(composeWebAnswer(text, hits), 'web');
          } else startModel();
        })();
        return;
      }

      // 3) MODEL fallback.
      startModel();
    },
    [messages, busy, auth.user, memory, brainChat, setConv, refreshConversations],
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
        onOpenCode={() => {
          setCodeOpen(true);
          setArchiveOpen(false);
        }}
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
            title="History"
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
        <button
          className="menu-toggle"
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-label="Menu"
        >
          ☰
        </button>
        <div className="hud-toggles" data-open={menuOpen}>
          <button
            className="sound-toggle"
            onClick={newChat}
            title="New chat"
          >
            <span aria-hidden="true">＋</span>
            <span>NEW</span>
          </button>
          <button
            className="sound-toggle"
            onClick={() => setCore3D((v) => !v)}
            aria-pressed={core3D}
            title="3D core on/off (performance)"
          >
            <span aria-hidden="true">◉</span>
            <span>{core3D ? '3D' : '2D'}</span>
          </button>
          <button
            className="sound-toggle"
            onClick={() => {
              const next = !brainOn;
              setLocalAnswerEnabled(next);
              setBrainOn(next);
            }}
            aria-pressed={brainOn}
            title="Answer source: local learned brain (offline, no key) vs. always the model"
          >
            <span aria-hidden="true">◈</span>
            <span>{brainOn ? 'BRAIN' : 'MODEL'}</span>
          </button>
          <button
            className="sound-toggle"
            onClick={() => {
              const next = !webOn;
              setWebSearchEnabled(next);
              setWebOn(next);
            }}
            aria-pressed={webOn}
            title="Web search when the local brain has no answer (keyless DuckDuckGo)"
          >
            <span aria-hidden="true">🌐</span>
            <span>{webOn ? 'WEB' : 'OFF'}</span>
          </button>
          <SoundToggle />
          <VoiceToggle />
          <button
            className="sound-toggle"
            onClick={() => setResidentsOn((v) => !v)}
            aria-pressed={residentsOn}
            title="Pixel residents on/off"
          >
            <span aria-hidden="true">👾</span>
            <span>{residentsOn ? 'CREW' : 'OFF'}</span>
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

      {memoryOpen && (
        <Suspense fallback={null}>
          <MemoryView memory={memory} onClose={() => setMemoryOpen(false)} />
        </Suspense>
      )}
      {codeOpen && (
        <Suspense fallback={null}>
          <CodeProjects onClose={() => setCodeOpen(false)} />
        </Suspense>
      )}
    </div>
  );
}
