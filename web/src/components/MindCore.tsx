import '../styles/addons.css';
import { Suspense, lazy, useMemo } from 'react';
import { type AuriState, STATE_PALETTE } from '../lib/auriState';
import { cssVars } from '../lib/ui';
import { prefersReducedMotion, supportsWebGL } from '../lib/webgl';
import ArcReactor from './ArcReactor';
import ErrorBoundary from './ErrorBoundary';

// Lazy so the heavy Three.js bundle only loads when we actually use 3D.
const MindCore3D = lazy(() => import('./MindCore3D'));

interface Props {
  state: AuriState;
  /** Force the lightweight 2D reactor (user toggle / weak GPU). */
  force2D?: boolean;
}

// The central "mind". On capable devices it shows the 3D golden energy sphere
// inside the 2D HUD ring frame; otherwise (no WebGL / reduced motion) it falls
// back to the original 2D cyan reactor so the centre is never empty.
export default function MindCore({ state, force2D }: Props) {
  const use3D = useMemo(() => supportsWebGL() && !prefersReducedMotion(), []);

  if (force2D || !use3D) {
    return <ArcReactor state={state} />;
  }

  const p = STATE_PALETTE[state];
  const ticks = Array.from({ length: 48 }, (_, i) => i);
  const fallback = <ArcReactor state={state} />;

  return (
    <div
      className="reactor reactor-3d"
      data-state={state}
      style={cssVars({ '--accent': p.accent, '--glow': p.glow, '--speed': p.speed })}
    >
      {/* 3D golden mind core in the centre */}
      <div className="mindcore-stage">
        <ErrorBoundary fallback={fallback}>
          <Suspense fallback={<div className="reactor-core" />}>
            <MindCore3D state={state} />
          </Suspense>
        </ErrorBoundary>
      </div>

      {/* 2D HUD ring frame around the sphere */}
      <svg className="reactor-svg reactor-frame" viewBox="0 0 200 200" aria-hidden="true">
        <circle className="ring ring-outer" cx="100" cy="100" r="92" />
        <g className="ring ring-arcs">
          <circle cx="100" cy="100" r="80" pathLength={100} />
        </g>
        <circle className="ring ring-mid" cx="100" cy="100" r="66" />
        <g className="ring ring-ticks">
          {ticks.map((i) => (
            <line
              key={i}
              x1="100"
              y1="44"
              x2="100"
              y2={i % 4 === 0 ? 38 : 41}
              transform={`rotate(${(360 / ticks.length) * i} 100 100)`}
            />
          ))}
        </g>
        <g className="reactor-cross">
          <line x1="100" y1="14" x2="100" y2="34" />
          <line x1="100" y1="166" x2="100" y2="186" />
          <line x1="14" y1="100" x2="34" y2="100" />
          <line x1="166" y1="100" x2="186" y2="100" />
        </g>
      </svg>

      <div className="reactor-status">{p.label}</div>
    </div>
  );
}
