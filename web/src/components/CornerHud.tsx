import type { AuriState } from '../lib/auriState';
import { useSysmon } from '../hooks/useSysmon';

interface Props {
  state: AuriState;
  mode: string;
}

// Corner telemetry — now REAL, machine-dependent data (CPU cores, RAM, GPU,
// JS-heap memory, render load/FPS, ping latency, connection, resolution, HTTPS,
// timezone). All read client-side; nothing leaves the browser. See lib/sysmon.
export default function CornerHud({ state, mode }: Props) {
  const { stat, live } = useSysmon();
  const tz = stat.timezone.split('/').pop() ?? stat.timezone;

  return (
    <div className="corner-hud" aria-hidden="true">
      <div className="corner tl">
        <span className="brk">⌜</span>
        <div className="corner-lines">
          <span>SYS {stat.cores}C{stat.memGB ? ` / ${stat.memGB}G` : ''}</span>
          <span>CORE {state.toUpperCase()}</span>
          <span>SRC {mode}</span>
        </div>
      </div>

      <div className="corner tr">
        <div className="corner-lines right">
          <span>PING {live.latencyMs != null ? `${live.latencyMs}ms` : '—'}</span>
          <span className={live.online ? 'ok' : 'bad'}>
            LINK {live.online ? live.netType.toUpperCase() : 'OFFLINE'} {live.online ? '●' : '○'}
          </span>
          <span>RES {stat.screen}</span>
        </div>
        <span className="brk">⌝</span>
      </div>

      <div className="corner bl">
        <span className="brk">⌞</span>
        <div className="corner-lines">
          <span>MEM {live.memPct != null ? `${live.memPct}%` : '—'}</span>
          <span>LOAD {live.loadPct}%</span>
          <span>v1.0 // AURI</span>
        </div>
      </div>

      <div className="corner br">
        <div className="corner-lines right">
          <span>FPS {live.fps || '—'}</span>
          <span>TZ {tz}</span>
          <span className={stat.secure ? 'ok' : 'bad'}>SECURE {stat.secure ? '✓' : '✗'}</span>
        </div>
        <span className="brk">⌟</span>
      </div>
    </div>
  );
}
