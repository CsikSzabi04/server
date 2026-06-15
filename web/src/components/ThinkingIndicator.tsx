// Shown after send, before the first token arrives. Pulsing dots + a small
// scanning ring, in the chat flow.
export default function ThinkingIndicator() {
  return (
    <div className="msg msg-auri">
      <div className="msg-tag">AURI</div>
      <div className="msg-body">
        <div className="thinking" role="status" aria-label="Auri gondolkodik">
          <span className="think-ring" />
          <span className="think-dots">
            <span />
            <span />
            <span />
          </span>
          <span className="think-label">PROCESSING…</span>
        </div>
      </div>
    </div>
  );
}
