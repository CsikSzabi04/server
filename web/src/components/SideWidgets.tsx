import { useEffect, useRef, useState } from 'react';

interface Props {
  tokens: number;
  latencyMs: number;
  speaking: boolean;
  mode: string;
}

function fmtUptime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

// Side monitoring widgets: uptime, tokens, latency, a fake load gauge, and a
// waveform that comes alive while Auri is "speaking".
export default function SideWidgets({ tokens, latencyMs, speaking, mode }: Props) {
  const start = useRef(Date.now());
  const [uptime, setUptime] = useState(0);
  const [load, setLoad] = useState(42);

  useEffect(() => {
    const id = window.setInterval(() => {
      setUptime((Date.now() - start.current) / 1000);
      setLoad((l) => Math.max(18, Math.min(96, l + (Math.random() - 0.5) * 18)));
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  const bars = Array.from({ length: 18 }, (_, i) => i);

  return (
    <aside className="side-widgets" aria-hidden="true">
      <div className="widget">
        <div className="widget-title">UPTIME</div>
        <div className="widget-value mono">{fmtUptime(uptime)}</div>
      </div>

      <div className="widget">
        <div className="widget-title">TOKENS</div>
        <div className="widget-value mono">{tokens.toLocaleString('en-US')}</div>
      </div>

      <div className="widget">
        <div className="widget-title">LATENCY</div>
        <div className="widget-value mono">{latencyMs ? `${latencyMs} ms` : '—'}</div>
      </div>

      <div className="widget">
        <div className="widget-title">CORE LOAD</div>
        <div className="gauge">
          <div className="gauge-fill" style={{ width: `${load}%` }} />
        </div>
        <div className="widget-sub mono">{Math.round(load)}% // {mode}</div>
      </div>

      <div className="widget widget-wave">
        <div className="widget-title">VOX</div>
        <div className={`wave${speaking ? ' wave-active' : ''}`}>
          {bars.map((i) => (
            <span key={i} style={{ animationDelay: `${i * 60}ms` }} />
          ))}
        </div>
      </div>
    </aside>
  );
}
