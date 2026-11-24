import { lazy, Suspense, useCallback, useEffect, useRef, useState, type ClipboardEvent, type DragEvent, type KeyboardEvent } from 'react';
import { blip } from '../lib/sound';
import { readDocument } from '../lib/files';
import { MAX_IMAGES, imageFiles, imageToDataUrl } from '../lib/images';
import { getPrefs, setMode, type ChatMode } from '../lib/modelStore';
import ModelPicker from './ModelPicker';

const CameraCapture = lazy(() => import('./CameraCapture'));

interface Props {
  disabled: boolean;
  onSend: (text: string, images?: string[]) => void;
  onTypingChange?: (typing: boolean) => void;
}

// Phones/tablets: the 📷 button opens the native camera (capture=environment);
// desktops: a small webcam dialog (falls back to the file picker without a camera).
const isTouch = () => typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches;

// Composer: textarea + send, with a file-upload (attach), images (Ctrl+V paste, drag & drop,
// 📎 pick, 📷 photo — sent to a vision model, kept in memory only), an Agent/Chat mode
// toggle, and the model picker. Mode + model live in modelStore (persisted);
// attached file text is folded into the outgoing message.
export default function InputBar({ disabled, onSend, onTypingChange }: Props) {
  const [value, setValue] = useState('');
  const [attached, setAttached] = useState<{ name: string; text: string } | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [imgBusy, setImgBusy] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const camRef = useRef<HTMLInputElement>(null);
  const [mode, setModeState] = useState<ChatMode>(getPrefs().mode);
  const [fileErr, setFileErr] = useState<string | null>(null);
  const typingTimer = useRef<number | undefined>(undefined);
  const fileRef = useRef<HTMLInputElement>(null);
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);

  // When the reply finishes, put the cursor back in the box — but ONLY if the user was
  // typing there when they sent (no autofocus on page load, no keyboard popping up on
  // phones while they read), and not while they're selecting text in the reply.
  const refocusAfterReply = useRef(false);
  useEffect(() => {
    if (disabled || !refocusAfterReply.current) return;
    refocusAfterReply.current = false;
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed) return; // user is selecting/copying reply text
    const active = document.activeElement;
    if (!active || active === document.body || composerRef.current?.contains(active)) fieldRef.current?.focus();
  }, [disabled]);

  const submit = () => {
    const text = value.trim(); // a picture alone is fine — no made-up text in the bubble
    const composed = attached
      ? `${text}\n\n[Attached file: ${attached.name}]\n${attached.text}`.trim()
      : text;
    if ((!composed && !images.length) || disabled || imgBusy) return;
    onSend(composed, images.length ? images : undefined);
    setValue('');
    setAttached(null);
    setImages([]);
    setFileErr(null);
    onTypingChange?.(false);
    refocusAfterReply.current = true;
    fieldRef.current?.focus(); // also after clicking SEND, so you can keep typing
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

  /** Screenshots / photos → compressed data: URLs waiting above the input (max MAX_IMAGES). */
  const addImages = async (files: Blob[]) => {
    if (!files.length) return;
    setFileErr(null);
    const room = MAX_IMAGES - images.length;
    if (room <= 0) {
      setFileErr(`Egy üzenetben legfeljebb ${MAX_IMAGES} kép lehet.`);
      return;
    }
    setImgBusy(true);
    try {
      const urls: string[] = [];
      for (const f of files.slice(0, room)) urls.push(await imageToDataUrl(f));
      setImages((prev) => [...prev, ...urls].slice(0, MAX_IMAGES));
      if (files.length > room) setFileErr(`Egy üzenetben legfeljebb ${MAX_IMAGES} kép lehet — a többit kihagytam.`);
      blip('recv');
      fieldRef.current?.focus();
    } catch (e) {
      setFileErr(`A képet nem sikerült beolvasni: ${(e as Error).message}`);
    } finally {
      setImgBusy(false);
    }
  };

  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = imageFiles(e.clipboardData);
    if (!files.length) return; // plain text paste → the browser handles it
    if (!e.clipboardData.getData('text/plain')) e.preventDefault();
    void addImages(files);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    setDragOver(false);
    const files = imageFiles(e.dataTransfer);
    if (files.length) {
      e.preventDefault();
      void addImages(files);
    } else if (e.dataTransfer.files?.[0]) {
      e.preventDefault();
      void pickFile(e.dataTransfer.files[0]);
    }
  };

  const openCamera = () => {
    if (isTouch()) camRef.current?.click();
    else setCameraOpen(true);
  };
  const cameraUnavailable = useCallback((reason: string) => {
    setCameraOpen(false);
    setFileErr(`${reason} Válassz egy képfájlt helyette.`);
    camRef.current?.click();
  }, []);
  const closeCamera = useCallback(() => setCameraOpen(false), []);

  const pickFile = async (f?: File | null) => {
    if (!f) return;
    if (f.type.startsWith('image/')) return void addImages([f]);
    setFileErr(null);
    try {
      const text = await readDocument(f);
      // The proxy accepts ~120k characters per request in total; a bigger attachment
      // would always fail. Large documents belong in MEMORY (searched in parts) instead.
      if (text.length > 90_000) {
        throw new Error('File too long to attach to a chat (max ~90k characters) — add it in MEMORY instead.');
      }
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
    <div
      ref={composerRef}
      className={`composer${disabled ? ' is-disabled' : ''}${dragOver ? ' is-dragover' : ''}`}
      onDragOver={(e) => {
        if (Array.from(e.dataTransfer.types).includes('Files')) {
          e.preventDefault();
          setDragOver(true);
        }
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragOver(false);
      }}
      onDrop={onDrop}
    >
      {(images.length > 0 || imgBusy) && (
        <div className="composer-images">
          {images.map((src, i) => (
            <div key={i} className="composer-thumb">
              <img src={src} alt={`Csatolt kép ${i + 1}`} />
              <button onClick={() => setImages((prev) => prev.filter((_, k) => k !== i))} aria-label="Kép eltávolítása">
                ✕
              </button>
            </div>
          ))}
          {imgBusy && <span className="composer-thumb-busy">kép feldolgozása…</span>}
        </div>
      )}
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
        {/* NOT `disabled` while Auri replies: a disabled field loses focus. It stays
            typeable (you can draft the next message); sending waits for the reply. */}
        <textarea
          ref={fieldRef}
          className="input-field"
          rows={1}
          placeholder={disabled ? 'AURI IS REPLYING…' : 'Message Auri…  (Enter = send, Shift+Enter = new line)'}
          value={value}
          aria-busy={disabled}
          onChange={(e) => {
            setValue(e.target.value);
            signalTyping();
          }}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
        />
        <button
          className="input-send"
          onClick={submit}
          disabled={disabled || imgBusy || (!value.trim() && !attached && !images.length)}
          aria-label="Send"
        >
          <span className="send-glyph">▶</span>
          <span className="send-label">SEND</span>
        </button>
      </div>

      <div className="composer-tools">
        <button
          className="composer-tool"
          onClick={() => fileRef.current?.click()}
          title="Fájl vagy kép csatolása (.txt, .md, .json, .csv, .log, kép) — képet Ctrl+V-vel is beilleszthetsz"
          disabled={disabled}
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.markdown,.json,.csv,.log,.text,image/png,image/jpeg,image/webp,image/gif"
          hidden
          onChange={(e) => {
            void pickFile(e.target.files?.[0]);
            e.target.value = ''; // the same file can be picked again
          }}
        />
        <button className="composer-tool" onClick={openCamera} title="Fénykép készítése" disabled={disabled}>
          📷
        </button>
        <input
          ref={camRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={(e) => {
            void addImages(Array.from(e.target.files ?? []));
            e.target.value = '';
          }}
        />
        {cameraOpen && (
          <Suspense fallback={null}>
            <CameraCapture
              onCapture={(b) => {
                setCameraOpen(false);
                void addImages([b]);
              }}
              onClose={closeCamera}
              onUnavailable={cameraUnavailable}
            />
          </Suspense>
        )}

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

      {/* EU AI Act art. 50 + SECURITY.md §17.4 (H-10): users must know they talk to an AI. */}
      <p className="composer-note">
        Auri egy mesterséges intelligencia — tévedhet, a fontos dolgokat ellenőrizd.{' '}
        <a href="/adatvedelem.html" target="_blank" rel="noopener">
          Adatvédelem
        </a>{' '}
        ·{' '}
        <a href="/feltetelek.html" target="_blank" rel="noopener">
          Feltételek
        </a>
      </p>
    </div>
  );
}
