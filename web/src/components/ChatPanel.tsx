import { useEffect, useRef } from 'react';
import type { UIMessage } from '../types';
import ChatMessage from './ChatMessage';
import ThinkingIndicator from './ThinkingIndicator';

interface Props {
  messages: UIMessage[];
  thinking: boolean;
}

export default function ChatPanel({ messages, thinking }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 'auto' (not smooth) so rapid token updates don't stack janky animations.
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, thinking]);

  return (
    <div className="chat-panel">
      <div className="chat-corner tl" aria-hidden="true" />
      <div className="chat-corner tr" aria-hidden="true" />
      <div className="chat-corner bl" aria-hidden="true" />
      <div className="chat-corner br" aria-hidden="true" />

      <div className="chat-scroll">
        {messages.map((m) => (
          <ChatMessage key={m.id} message={m} />
        ))}
        {thinking && <ThinkingIndicator />}
        <div ref={endRef} />
      </div>
    </div>
  );
}
