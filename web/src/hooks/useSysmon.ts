import { useEffect, useState } from 'react';
import { SYS_STATIC, subscribeSys, type SysLive, type SysStatic } from '../lib/sysmon';

// Subscribe to the shared live telemetry singleton (one rAF loop + one poll for
// the whole app, regardless of how many widgets consume it).
export function useSysmon(): { stat: SysStatic; live: SysLive } {
  const [live, setLive] = useState<SysLive>({
    fps: 0,
    loadPct: 0,
    memPct: null,
    memUsedMB: null,
    latencyMs: null,
    online: navigator.onLine,
    netType: 'n/a',
    downlink: null,
    battery: null,
    charging: null,
  });
  useEffect(() => subscribeSys(setLive), []);
  return { stat: SYS_STATIC, live };
}
