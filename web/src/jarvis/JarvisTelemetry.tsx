// AI-3 (BODY) — the AuriGPT side widgets (UPTIME · TOKENS · LATENCY · CORE LOAD · RIG · VOX),
// compacted into a 3×2 strip for the desktop HUD's left column. Unlike the web version the
// numbers come from the daemon where it knows better: CORE LOAD = the machine's real CPU/RAM
// (psutil, `stats` event), LATENCY = the last voice turn (`timing`), TOKENS = the LLM output
// tokens of this session (`reply.done.tokens`), VOX = the live mic / speaker level (`level`).
// RIG + FPS stay browser-side (useSysmon). Nothing here leaves the machine.
import { memo, useEffect, useRef, useState } from 'react';
import { useSysmon } from '../hooks/useSysmon';
import type { JarvisModel } from './useJarvisSocket';

const BARS = 18;

function fmtUptime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

function fmtMs(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return v >= 10_000 ? `${(v / 1000).toFixed(1)} s` : `${Math.round(v)} ms`;
}

// Own 1 s tick so the whole HUD doesn't re-render every second.
const Uptime = memo(function Uptime() {
  const start = useRef(Date.now());
  const [sec, setSec] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setSec((Date.now() - start.current) / 1000), 1000);
    return () => window.clearInterval(id);
  }, []);
  return <>{fmtUptime(sec)}</>;
});

// A scrolling level meter: every 90 ms the current rms is pushed in from the right.
// rms is small (speech ≈ 0.02–0.2) → sqrt scaling so quiet speech still moves the bars.
const Vox = memo(function Vox({ level, source }: { level: number; source: 'mic' | 'out' | null }) {
  const levelRef = useRef(level);
  levelRef.current = level;
  const [hist, setHist] = useState<number[]>(() => Array(BARS).fill(0));
  const active = source !== null;
  useEffect(() => {
    if (!active) {
      setHist(Array(BARS).fill(0));
      return;
    }
    const id = window.setInterval(() => {
      const h = Math.min(1, Math.sqrt(Math.max(0, levelRef.current)) * 2.4);
      setHist((prev) => [...prev.slice(1), h]);
    }, 90);
    return () => window.clearInterval(id);
  }, [active]);
  return (
    <div className={`jv-tel-wave${active ? ' on' : ''}${source === 'mic' ? ' mic' : ''}`}>
      {hist.map((h, i) => (
        <span key={i} style={{ height: `${Math.round(12 + h * 88)}%` }} />
      ))}
    </div>
  );
});

function Gauge({ label, pct }: { label: string; pct: number | null }) {
  return (
    <div className="jv-tel-g">
      <span>{label}</span>
      <div className="jv-tel-gauge">
        <div className={`jv-tel-fill${pct !== null && pct >= 85 ? ' hot' : ''}`} style={{ width: `${pct ?? 0}%` }} />
      </div>
      <b>{pct ?? '—'}%</b>
    </div>
  );
}

export default function JarvisTelemetry({ model, connected }: { model: JarvisModel; connected: boolean }) {
  const { stat, live } = useSysmon();
  const last = model.timings[model.timings.length - 1];
  const cpu = model.stats?.cpu ?? null;
  const ram = model.stats?.ram ?? null;
  const source = !connected ? null : model.state === 'speaking' ? 'out' : model.state === 'listening' ? 'mic' : null;
  const level = source === 'out' ? model.out : source === 'mic' ? model.mic : 0;

  return (
    <div className="jv-tel" aria-label="Telemetria">
      <div className="jv-tel-w">
        <div className="jv-tel-t">UPTIME</div>
        <div className="jv-tel-v">
          <Uptime />
        </div>
      </div>

      <div className="jv-tel-w">
        <div className="jv-tel-t">TOKENS</div>
        <div className="jv-tel-v">{model.tokens.toLocaleString('en-US')}</div>
        <div className="jv-tel-s">{model.replyModel ?? 'ebben a munkamenetben'}</div>
      </div>

      <div className="jv-tel-w">
        <div className="jv-tel-t">LATENCY</div>
        <div className="jv-tel-v">{fmtMs(last?.total_ms)}</div>
        <div className="jv-tel-s">LLM {fmtMs(last?.llm_first_ms)} · TTS {fmtMs(last?.tts_first_ms)}</div>
      </div>

      <div className="jv-tel-w" title={`HUD: ${live.fps || '—'} FPS`}>
        <div className="jv-tel-t">CORE LOAD</div>
        <Gauge label="CPU" pct={cpu} />
        <Gauge label="RAM" pct={ram} />
      </div>

      <div className="jv-tel-w">
        <div className="jv-tel-t">RIG</div>
        <div className="jv-tel-s strong">
          {stat.cores}C{stat.memGB ? ` / ${stat.memGB}G` : ''} · {stat.screen}
        </div>
        <div className="jv-tel-s" title={stat.gpu}>
          {stat.gpu}
          {/* a desktop without a battery reports "100 % charging" — only show a real one */}
          {live.battery != null && !(live.battery >= 100 && live.charging) ? ` · BAT ${live.battery}%${live.charging ? '⚡' : ''}` : ''}
        </div>
      </div>

      <div className="jv-tel-w">
        <div className="jv-tel-t">
          VOX <small>{source === 'mic' ? '· MIC' : source === 'out' ? '· OUT' : ''}</small>
        </div>
        <Vox level={level} source={source} />
      </div>
    </div>
  );
}
