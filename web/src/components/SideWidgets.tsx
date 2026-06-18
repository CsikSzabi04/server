import { useEffect, useRef, useState } from 'react';
import { useSysmon } from '../hooks/useSysmon';

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

// Side monitoring widgets — REAL telemetry now: render load/FPS + JS-heap memory,
// the machine's CPU/RAM/GPU/resolution (RIG), plus session uptime, AI token count
// and API latency. The VOX waveform comes alive while Auri is "speaking".
export default function SideWidgets({ tokens, latencyMs, speaking, mode }: Props) {
  const start = useRef(Date.now());
  const [uptime, setUptime] = useState(0);
  const { stat, live } = useSysmon();

  useEffect(() => {
    const id = window.setInterval(() => setUptime((Date.now() - start.current) / 1000), 1000);
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
          <div className="gauge-fill" style={{ width: `${live.loadPct}%` }} />
        </div>
        <div className="widget-sub mono">
          {live.fps || '—'} FPS · {live.memPct != null ? `${live.memPct}% MEM` : mode}
        </div>
      </div>

      <div className="widget">
        <div className="widget-title">RIG</div>
        <div className="widget-sub mono">
          {stat.cores}C{stat.memGB ? ` / ${stat.memGB}G` : ''} · {stat.dpr}× · {stat.screen}
        </div>
        <div className="widget-sub mono" style={{ opacity: 0.7 }} title={stat.gpu}>
          {stat.gpu}
          {live.battery != null ? ` · BAT ${live.battery}%${live.charging ? '⚡' : ''}` : ''}
        </div>
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
