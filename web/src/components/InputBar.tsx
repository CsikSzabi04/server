import { useRef, useState, type KeyboardEvent } from 'react';
import { blip } from '../lib/sound';

interface Props {
  disabled: boolean;
  onSend: (text: string) => void;
  onTypingChange?: (typing: boolean) => void;
}

export default function InputBar({ disabled, onSend, onTypingChange }: Props) {
  const [value, setValue] = useState('');
  const typingTimer = useRef<number | undefined>(undefined);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
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

  return (
    <div className={`input-bar${disabled ? ' is-disabled' : ''}`}>
      <span className="input-prompt">›</span>
      <textarea
        className="input-field"
        rows={1}
        placeholder={disabled ? 'AURI VÁLASZOL…' : 'Írj Aurinak…  (Enter = küldés, Shift+Enter = új sor)'}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          setValue(e.target.value);
          signalTyping();
        }}
        onKeyDown={onKeyDown}
      />
      <button className="input-send" onClick={submit} disabled={disabled || !value.trim()} aria-label="Küldés">
        <span className="send-glyph">▶</span>
        <span className="send-label">SEND</span>
      </button>
    </div>
  );
}
