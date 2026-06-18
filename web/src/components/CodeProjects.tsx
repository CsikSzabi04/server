import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  type CodeProject,
  type ProjectKind,
  KINDS,
  kindIcon,
  listProjects,
  createProject,
  saveProject,
  renameProject,
  deleteProject,
  downloadZip,
  learnFromProject,
  learningsPrompt,
} from '../lib/codeProjects';
import { type ChatMessage, streamChat } from '../lib/api';
import { useBrainChat } from '../brain-bridge/brainChat';
import '../styles/code.css';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
}

interface Block {
  lang: string;
  code: string;
}

/** All fenced code blocks in an assistant reply. */
function extractCodeBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const re = /```([a-zA-Z0-9.+#-]*)\n([\s\S]*?)```/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) blocks.push({ lang: m[1] || '', code: m[2].replace(/\n+$/, '') });
  return blocks;
}

/** The prose around the code blocks, so we don't print the code twice. */
function stripCode(text: string): string {
  return text.replace(/```[\s\S]*?```/g, '').replace(/\n{3,}/g, '\n\n').trim();
}

type DiffRow = { type: 'same' | 'add' | 'del'; text: string };

/** Compact LCS line diff (fine for the small files the chat produces). */
function diffLines(a: string, b: string): DiffRow[] {
  const oldL = a.split('\n');
  const newL = b.split('\n');
  const n = oldL.length;
  const m = newL.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = oldL[i] === newL[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (oldL[i] === newL[j]) {
      out.push({ type: 'same', text: oldL[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ type: 'del', text: oldL[i++] });
    } else {
      out.push({ type: 'add', text: newL[j++] });
    }
  }
  while (i < n) out.push({ type: 'del', text: oldL[i++] });
  while (j < m) out.push({ type: 'add', text: newL[j++] });
  return out;
}

// Full-screen code workspace: separate projects (Python / Node / React / JS /
// Java), an editor, and an Auri chat that sees the active file and can rewrite
// it. Code-tuned (low temperature), shows a diff before applying, and learns the
// user's libraries + naming style from every write. Edits autosave to localStorage.
export default function CodeProjects({ onClose }: { onClose: () => void }) {
  const [projects, setProjects] = useState<CodeProject[]>([]);
  const [selId, setSelId] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newKind, setNewKind] = useState<ProjectKind>('python');

  const [chat, setChat] = useState<Msg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [diffKey, setDiffKey] = useState<string | null>(null);
  const chatAbort = useRef<AbortController | null>(null);
  const chatEnd = useRef<HTMLDivElement | null>(null);
  const learnTimer = useRef<number | null>(null);
  const brainChat = useBrainChat(); // hybrid: brain grounds the model + learns every prompt

  useEffect(() => {
    const list = listProjects();
    setProjects(list);
    if (list.length) {
      setSelId(list[0].id);
      setActivePath(list[0].files[0]?.path ?? null);
    }
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  // Stop any in-flight request and pending learn when the panel unmounts.
  useEffect(
    () => () => {
      chatAbort.current?.abort();
      if (learnTimer.current) window.clearTimeout(learnTimer.current);
    },
    [],
  );

  const sel = projects.find((p) => p.id === selId) ?? null;
  const activeFile = sel?.files.find((f) => f.path === activePath) ?? null;

  const persist = (updated: CodeProject) => {
    saveProject(updated);
    setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  /** Learn from a project shortly after the latest change settles. */
  const scheduleLearn = (project: CodeProject) => {
    if (learnTimer.current) window.clearTimeout(learnTimer.current);
    learnTimer.current = window.setTimeout(() => learnFromProject(project), 1500);
  };

  const withFile = (path: string, content: string): CodeProject | null => {
    if (!sel) return null;
    return {
      ...sel,
      files: sel.files.map((f) => (f.path === path ? { ...f, content } : f)),
      updatedAt: new Date().toISOString(),
    };
  };

  // Manual editing: autosave + debounced learning.
  const editActiveFile = (content: string) => {
    if (!activeFile) return;
    const updated = withFile(activeFile.path, content);
    if (updated) {
      persist(updated);
      scheduleLearn(updated);
    }
  };

  // Applying Auri's code: autosave + learn immediately (this is a real signal).
  const applyCode = (code: string) => {
    if (!activeFile) return;
    const updated = withFile(activeFile.path, code);
    if (updated) {
      persist(updated);
      learnFromProject(updated);
    }
    setDiffKey(null);
  };

  const onCreate = () => {
    const p = createProject(newName, newKind);
    setNewName('');
    setProjects(listProjects());
    setSelId(p.id);
    setActivePath(p.files[0]?.path ?? null);
  };

  const onSelectProject = (id: string) => {
    setSelId(id);
    setActivePath(projects.find((p) => p.id === id)?.files[0]?.path ?? null);
  };

  const addFile = () => {
    if (!sel) return;
    const path = window.prompt('New file path (e.g. src/utils.js):')?.trim();
    if (!path || sel.files.some((f) => f.path === path)) return;
    persist({ ...sel, files: [...sel.files, { path, content: '' }], updatedAt: new Date().toISOString() });
    setActivePath(path);
  };

  const removeFile = (path: string) => {
    if (!sel || sel.files.length <= 1) return;
    if (!window.confirm(`Delete ${path}?`)) return;
    const updated = { ...sel, files: sel.files.filter((f) => f.path !== path), updatedAt: new Date().toISOString() };
    persist(updated);
    if (activePath === path) setActivePath(updated.files[0]?.path ?? null);
  };

  const onRenameProject = (id: string) => {
    const t = window.prompt('Project name:', projects.find((p) => p.id === id)?.name ?? '');
    if (!t?.trim()) return;
    renameProject(id, t.trim());
    setProjects(listProjects());
  };

  const onDeleteProject = (id: string) => {
    if (!window.confirm('Delete this project?')) return;
    deleteProject(id);
    const list = listProjects();
    setProjects(list);
    if (selId === id) {
      setSelId(list[0]?.id ?? null);
      setActivePath(list[0]?.files[0]?.path ?? null);
    }
  };

  // ── Auri chat: shapes code with the active file + learned conventions ──────
  const sendChat = () => {
    const text = chatInput.trim();
    if (!text || chatBusy) return;
    setChatInput('');

    const learned = sel ? learningsPrompt(sel.kind) : null;
    const base =
      sel && activeFile
        ? `You are Auri, an expert pair-programmer working inside a code editor.\n` +
          `Project: "${sel.name}" (${sel.kind}). Active file: ${activeFile.path}.\n` +
          `Current contents of ${activeFile.path}:\n\`\`\`\n${activeFile.content}\n\`\`\`\n` +
          `When the user asks you to write or change code, reply with a SHORT explanation, then give the COMPLETE updated contents of the file in ONE fenced code block. Keep it correct, runnable and idiomatic. Answer in the user's language.`
        : `You are Auri, an expert programming assistant. Help the user write clean, complete, runnable code. When you produce a file, wrap it in one fenced code block. Answer in the user's language.`;
    const sys = [base, learned].filter(Boolean).join('\n\n');

    // Hybrid H1: ground the model in what the brain already knows (relevant facts, code
    // snippets + sources, related concepts) so the model answers from our brain too.
    const brainCtx = brainChat.groundContext(text, []);
    const history: ChatMessage[] = [
      { role: 'system', content: sys },
      ...(brainCtx ? [{ role: 'system' as const, content: brainCtx }] : []),
      ...chat.map((m) => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    setChat((prev) => [...prev, { role: 'user', content: text }]);
    setChatBusy(true);

    let assistantText = '';
    let created = false;
    const ctrl = new AbortController();
    chatAbort.current = ctrl;

    void streamChat(
      history,
      {
        onDelta: (d) => {
          assistantText += d;
          if (!created) {
            created = true;
            setChat((prev) => [...prev, { role: 'assistant', content: assistantText }]);
          } else {
            setChat((prev) => {
              const copy = prev.slice();
              copy[copy.length - 1] = { role: 'assistant', content: assistantText };
              return copy;
            });
          }
        },
        onDone: () => {
          setChatBusy(false);
          // Hybrid H2: distil EVERY code prompt+answer into the brain → it learns the
          // libraries/patterns and can help (or answer) more on its own next time.
          if (assistantText.trim()) brainChat.distill(text, assistantText);
        },
        onError: (msg) => {
          if (!created) setChat((prev) => [...prev, { role: 'assistant', content: msg }]);
          setChatBusy(false);
        },
      },
      ctrl.signal,
      // Code wants determinism + room for a full file.
      { temperature: 0.2, maxTokens: 2048 },
    );
  };

  return createPortal(
    <div className="code-screen">
      <div className="code-modal" onClick={(e) => e.stopPropagation()}>
        <div className="code-head">
          <span className="auth-title">{'</>'} CODE PROJECTS</span>
          <button className="auth-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="code-body">
          <aside className="code-projects">
            <div className="code-new">
              <input
                className="auth-input code-new-name"
                placeholder="project name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onCreate()}
              />
              <select
                className="auth-input code-kind"
                value={newKind}
                onChange={(e) => setNewKind(e.target.value as ProjectKind)}
              >
                {KINDS.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.icon} {k.label}
                  </option>
                ))}
              </select>
              <button className="archive-new code-create" onClick={onCreate}>
                ＋ NEW PROJECT
              </button>
            </div>

            <div className="code-proj-list">
              {projects.length === 0 && <div className="archive-empty">No projects yet.</div>}
              {projects.map((p) => (
                <div
                  key={p.id}
                  className={`code-proj${p.id === selId ? ' code-proj--active' : ''}`}
                  onClick={() => onSelectProject(p.id)}
                >
                  <div className="code-proj-main">
                    <div className="code-proj-name">
                      {kindIcon(p.kind)} {p.name}
                    </div>
                    <div className="code-proj-meta">
                      {p.kind} · {p.files.length} files
                    </div>
                  </div>
                  <div className="code-proj-actions" onClick={(e) => e.stopPropagation()}>
                    <button title="Download .zip" onClick={() => downloadZip(p)}>
                      ⬇
                    </button>
                    <button title="Rename" onClick={() => onRenameProject(p.id)}>
                      ✎
                    </button>
                    <button title="Delete" onClick={() => onDeleteProject(p.id)}>
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </aside>

          <section className="code-editor">
            {!sel ? (
              <div className="code-placeholder">Create or pick a project to start.</div>
            ) : (
              <>
                <div className="code-files">
                  {sel.files.map((f) => (
                    <button
                      key={f.path}
                      className={`code-file-tab${f.path === activePath ? ' code-file-tab--active' : ''}`}
                      onClick={() => setActivePath(f.path)}
                    >
                      {f.path}
                      {sel.files.length > 1 && (
                        <span
                          className="code-file-x"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeFile(f.path);
                          }}
                        >
                          ✕
                        </span>
                      )}
                    </button>
                  ))}
                  <button className="code-file-add" onClick={addFile} title="Add file">
                    ＋
                  </button>
                </div>

                {activeFile ? (
                  <textarea
                    className="code-area"
                    spellCheck={false}
                    value={activeFile.content}
                    onChange={(e) => editActiveFile(e.target.value)}
                    placeholder="// write code…"
                  />
                ) : (
                  <div className="code-placeholder">No file selected.</div>
                )}

                <div className="code-toolbar">
                  <span className="code-hint">
                    {kindIcon(sel.kind)} {sel.name} · {sel.kind} · autosaved + learning
                  </span>
                  <button className="auth-submit code-dl" onClick={() => downloadZip(sel)}>
                    ⬇ Download .zip
                  </button>
                </div>
              </>
            )}
          </section>

          <aside className="code-chat">
            <div className="code-chat-head">
              <span>◈ ASK AURI</span>
              {activeFile && <span className="code-chat-ctx">{activeFile.path}</span>}
            </div>

            <div className="code-chat-list">
              {chat.length === 0 && (
                <div className="code-chat-hint">
                  Ask Auri to write or change the open file — e.g. “add a fetch() helper”, “convert
                  this to TypeScript”. Auri learns the libraries &amp; naming style you use. Review the
                  diff, then apply with one click.
                </div>
              )}
              {chat.map((m, i) => {
                if (m.role === 'user') {
                  return (
                    <div key={i} className="code-msg code-msg--user">
                      <div className="code-msg-role">YOU</div>
                      <div className="code-msg-text">{m.content}</div>
                    </div>
                  );
                }
                const prose = stripCode(m.content);
                const blocks = extractCodeBlocks(m.content);
                return (
                  <div key={i} className="code-msg code-msg--assistant">
                    <div className="code-msg-role">AURI</div>
                    {prose && <div className="code-msg-text">{prose}</div>}
                    {blocks.map((b, bi) => {
                      const key = `${i}:${bi}`;
                      const open = diffKey === key;
                      return (
                        <div key={bi} className="code-block">
                          <div className="code-block-bar">
                            <span className="code-block-lang">{b.lang || 'code'}</span>
                            {activeFile && (
                              <span className="code-block-acts">
                                <button
                                  className="code-block-btn"
                                  onClick={() => setDiffKey(open ? null : key)}
                                >
                                  {open ? 'Hide diff' : '⤳ Diff'}
                                </button>
                                <button className="code-apply" onClick={() => applyCode(b.code)}>
                                  ⬇ Apply to {activeFile.path}
                                </button>
                              </span>
                            )}
                          </div>
                          {open && activeFile ? (
                            <div className="code-diff">
                              {diffLines(activeFile.content, b.code).map((d, di) => (
                                <div key={di} className={`code-diff-line code-diff--${d.type}`}>
                                  <span className="code-diff-sign">
                                    {d.type === 'add' ? '+' : d.type === 'del' ? '-' : ' '}
                                  </span>
                                  {d.text}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <pre className="code-block-pre">{b.code}</pre>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
              <div ref={chatEnd} />
            </div>

            <div className="code-chat-form">
              <textarea
                className="auth-input code-chat-input"
                placeholder={chatBusy ? 'Auri is thinking…' : 'Ask Auri to shape the code…'}
                value={chatInput}
                disabled={chatBusy}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChat();
                  }
                }}
              />
              <button
                className="auth-submit code-chat-send"
                onClick={sendChat}
                disabled={chatBusy || !chatInput.trim()}
              >
                {chatBusy ? '…' : 'Send ▸'}
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>,
    document.body,
  );
}
