import { useRef, useState, type KeyboardEvent } from 'react';
import { blip } from '../lib/sound';
import { readDocument } from '../lib/files';
import { getPrefs, setMode, type ChatMode } from '../lib/modelStore';
import ModelPicker from './ModelPicker';

interface Props {
  disabled: boolean;
  onSend: (text: string) => void;
  onTypingChange?: (typing: boolean) => void;
}

// Composer: textarea + send, with a file-upload (attach), an Agent/Chat mode
// toggle, and the model picker. Mode + model live in modelStore (persisted);
// attached file text is folded into the outgoing message, so the send signature
// stays unchanged.
export default function InputBar({ disabled, onSend, onTypingChange }: Props) {
  const [value, setValue] = useState('');
  const [attached, setAttached] = useState<{ name: string; text: string } | null>(null);
  const [mode, setModeState] = useState<ChatMode>(getPrefs().mode);
  const [fileErr, setFileErr] = useState<string | null>(null);
  const typingTimer = useRef<number | undefined>(undefined);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    const text = value.trim();
    const composed = attached
      ? `${text}\n\n[Attached file: ${attached.name}]\n${attached.text}`.trim()
      : text;
    if (!composed || disabled) return;
    onSend(composed);
    setValue('');
    setAttached(null);
    setFileErr(null);
    onTypingChange?.(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    } else {
      blip('type');
    }
  };

  const signalTyping = () => {
    onTypingChange?.(true);
    window.clearTimeout(typingTimer.current);
    typingTimer.current = window.setTimeout(() => onTypingChange?.(false), 1200);
  };

  const pickFile = async (f?: File | null) => {
    if (!f) return;
    setFileErr(null);
    try {
      const text = await readDocument(f);
      setAttached({ name: f.name, text });
      blip('recv');
    } catch (e) {
      setAttached(null);
      setFileErr((e as Error).message);
    }
  };

  const setModeBoth = (m: ChatMode) => {
    if (m === mode) return;
    setMode(m);
    setModeState(m);
    blip('type');
  };

  return (
    <div className={`composer${disabled ? ' is-disabled' : ''}`}>
      {attached && (
        <div className="composer-attach">
          <span className="composer-chip">📎 {attached.name}</span>
          <button onClick={() => setAttached(null)} aria-label="Remove attachment">
            ✕
          </button>
        </div>
      )}
      {fileErr && <div className="composer-err">{fileErr}</div>}

      <div className="input-bar">
        <span className="input-prompt">›</span>
        <textarea
          className="input-field"
          rows={1}
          placeholder={disabled ? 'AURI IS REPLYING…' : 'Message Auri…  (Enter = send, Shift+Enter = new line)'}
          value={value}
          disabled={disabled}
          onChange={(e) => {
            setValue(e.target.value);
            signalTyping();
          }}
          onKeyDown={onKeyDown}
        />
        <button className="input-send" onClick={submit} disabled={disabled || (!value.trim() && !attached)} aria-label="Send">
          <span className="send-glyph">▶</span>
          <span className="send-label">SEND</span>
        </button>
      </div>

      <div className="composer-tools">
        <button
          className="composer-tool"
          onClick={() => fileRef.current?.click()}
          title="Attach a file (.txt, .md, .json, .csv, .log)"
          disabled={disabled}
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.markdown,.json,.csv,.log,.text"
          hidden
          onChange={(e) => void pickFile(e.target.files?.[0])}
        />

        <div className="composer-spacer" />

        <div className="mode-toggle" role="group" aria-label="Mode">
          <button className={mode === 'agent' ? 'on' : ''} onClick={() => setModeBoth('agent')} title="Proactive, step-by-step">
            Agent
          </button>
          <button className={mode === 'chat' ? 'on' : ''} onClick={() => setModeBoth('chat')} title="Conversational">
            Chat
          </button>
        </div>

        <ModelPicker />
      </div>
    </div>
  );
}
