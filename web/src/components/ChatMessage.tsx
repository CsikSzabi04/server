import type { UIMessage } from '../types';
import MessageContent from './MessageContent';

interface Props {
  message: UIMessage;
}

export default function ChatMessage({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="msg msg-user">
        <div className="msg-tag">USER</div>
        {message.images?.length ? (
          <div className="msg-images">
            {message.images.map((src, i) => (
              <img key={i} src={src} alt={`Csatolt kép ${i + 1}`} />
            ))}
          </div>
        ) : null}
        {message.content && <div className="msg-body">{message.content}</div>}
      </div>
    );
  }

  return (
    <div className={`msg msg-auri${message.error ? ' msg-error' : ''}`}>
      <div className="msg-tag">
        {message.error ? '!! AURI' : 'AURI'}
        {message.source && (
          <span className={`msg-src msg-src--${message.source}`}>
            {message.source === 'brain'
              ? '◈ brain'
              : message.source === 'web'
                ? '🌐 web'
                : message.source === 'brain-model'
                  ? '◈ brain+model'
                  : 'model'}
          </span>
        )}
      </div>
      <div className="msg-body">
        <MessageContent text={message.content} streaming={Boolean(message.streaming)} />
      </div>
    </div>
  );
}
