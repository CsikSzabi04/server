import type { UIMessage } from '../types';
import LiveText from './LiveText';

interface Props {
  message: UIMessage;
}

export default function ChatMessage({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="msg msg-user">
        <div className="msg-tag">USER</div>
        <div className="msg-body">{message.content}</div>
      </div>
    );
  }

  return (
    <div className={`msg msg-auri${message.error ? ' msg-error' : ''}`}>
      <div className="msg-tag">{message.error ? '!! AURI' : 'AURI'}</div>
      <div className="msg-body">
        <LiveText text={message.content} streaming={Boolean(message.streaming)} />
      </div>
    </div>
  );
}
