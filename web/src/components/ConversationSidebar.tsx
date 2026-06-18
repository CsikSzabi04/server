import { useState } from 'react';
import type { ConversationMeta } from '../lib/chatStore';

interface Props {
  open: boolean;
  onClose: () => void;
  conversations: ConversationMeta[];
  currentId: string | null;
  onNew: () => void;
  onOpenCode: () => void;
  onOpen: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onPin: (id: string, pinned: boolean) => void;
}

function relTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (!t) return '';
  const s = Math.floor((Date.now() - t) / 1000);
  if (s < 60) return 'now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function ConversationSidebar({
  open,
  onClose,
  conversations,
  currentId,
  onNew,
  onOpenCode,
  onOpen,
  onRename,
  onDelete,
  onPin,
}: Props) {
  const [q, setQ] = useState('');

  const query = q.trim().toLowerCase();
  const list = query
    ? conversations.filter(
        (c) =>
          c.title.toLowerCase().includes(query) ||
          (c.keywords ?? []).some((k) => k.toLowerCase().includes(query)),
      )
    : conversations;

  return (
    <aside className={`archive${open ? ' archive--open' : ''}`} aria-hidden={!open}>
      <div className="archive-head">
        <span className="archive-title">ARCHIVE</span>
        <button className="archive-x" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      <div className="archive-tools">
        <button className="archive-code" onClick={onOpenCode}>
          {'</>'} CODE
        </button>
        <button
          className="archive-code archive-brain"
          onClick={() => {
            onClose();
            window.location.hash = 'brain';
          }}
        >
          ◈ BRAIN
        </button>
      </div>

      <button className="archive-new" onClick={onNew}>
        ＋ NEW CHAT
      </button>

      <input
        className="archive-search"
        placeholder="search…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      <div className="archive-list">
        {list.length === 0 && <div className="archive-empty">No conversations yet.</div>}
        {list.map((c) => (
          <div
            key={c.id}
            className={`archive-item${c.id === currentId ? ' archive-item--active' : ''}`}
            onClick={() => onOpen(c.id)}
          >
            <div className="archive-item-main">
              <div className="archive-item-title">
                {c.pinned && <span className="archive-pin-dot">★</span>}
                {c.title}
              </div>
              <div className="archive-item-meta">
                <span>{relTime(c.updatedAt)}</span>
                {c.keywords && c.keywords[0] && <span className="archive-chip">{c.keywords[0]}</span>}
              </div>
            </div>
            <div className="archive-actions" onClick={(e) => e.stopPropagation()}>
              <button
                title={c.pinned ? 'Unpin' : 'Pin to top'}
                onClick={() => onPin(c.id, !c.pinned)}
              >
                {c.pinned ? '★' : '☆'}
              </button>
              <button
                title="Rename"
                onClick={() => {
                  const t = window.prompt('New title:', c.title);
                  if (t && t.trim()) onRename(c.id, t.trim());
                }}
              >
                ✎
              </button>
              <button
                title="Delete"
                onClick={() => {
                  if (window.confirm('Delete this conversation?')) onDelete(c.id);
                }}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
