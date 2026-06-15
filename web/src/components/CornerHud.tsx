import { useEffect, useState } from 'react';
import type { AuriState } from '../lib/auriState';
import { hex } from '../lib/ui';

interface Props {
  state: AuriState;
  mode: string;
}

interface Telemetry {
  sys: string;
  lat: string;
  rgba: number;
  mem: number;
  uplink: boolean;
}

function gen(): Telemetry {
  return {
    sys: hex(Math.floor(Math.random() * 255)),
    lat: (46 + Math.random()).toFixed(2),
    rgba: Math.floor(1000 + Math.random() * 8999),
    mem: Math.floor(38 + Math.random() * 56),
    uplink: Math.random() > 0.06,
  };
}

// Decorative corner telemetry that periodically refreshes/flickers to sell the
// "live system" feel. Purely cosmetic except for `state`/`mode`.
export default function CornerHud({ state, mode }: Props) {
  const [t, setT] = useState<Telemetry>(gen);

  useEffect(() => {
    const id = window.setInterval(() => setT(gen()), 1500);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="corner-hud" aria-hidden="true">
      <div className="corner tl">
        <span className="brk">⌜</span>
        <div className="corner-lines">
          <span>SYS 0x{t.sys}</span>
          <span>CORE {state.toUpperCase()}</span>
          <span>SRC {mode}</span>
        </div>
      </div>

      <div className="corner tr">
        <div className="corner-lines right">
          <span>LAT {t.lat}°</span>
          <span className={t.uplink ? 'ok' : 'bad'}>UPLINK {t.uplink ? '●' : '○'}</span>
          <span>RGBA {t.rgba}</span>
        </div>
        <span className="brk">⌝</span>
      </div>

      <div className="corner bl">
        <span className="brk">⌞</span>
        <div className="corner-lines">
          <span>MEM {t.mem}%</span>
          <span>BUS ▰▰▰▱▱</span>
          <span>v1.0 // AURI</span>
        </div>
      </div>

      <div className="corner br">
        <div className="corner-lines right">
          <span>SCAN ▱▰▱▰▱</span>
          <span>GEO 47.49 / 19.04</span>
          <span>SECURE ✓</span>
        </div>
        <span className="brk">⌟</span>
      </div>
    </div>
  );
}
