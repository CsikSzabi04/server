import { type AuriState, STATE_PALETTE } from '../lib/auriState';
import { cssVars } from '../lib/ui';

interface Props {
  state: AuriState;
}

// State-driven central reactor. Color + spin speed come from the palette via CSS
// custom properties; the actual rotation/pulse is done in hud.css so it stays
// GPU-friendly and interpolates smoothly between states.
export default function ArcReactor({ state }: Props) {
  const p = STATE_PALETTE[state];

  // Tick marks around the inner ring.
  const ticks = Array.from({ length: 48 }, (_, i) => i);

  return (
    <div
      className="reactor"
      data-state={state}
      style={cssVars({ '--accent': p.accent, '--glow': p.glow, '--speed': p.speed })}
    >
      <svg className="reactor-svg" viewBox="0 0 200 200" aria-hidden="true">
        {/* outer dashed ring — slow CW */}
        <circle className="ring ring-outer" cx="100" cy="100" r="92" />
        {/* segmented arcs — CCW */}
        <g className="ring ring-arcs">
          <circle cx="100" cy="100" r="80" pathLength={100} />
        </g>
        {/* mid dotted ring — CW faster */}
        <circle className="ring ring-mid" cx="100" cy="100" r="66" />
        {/* tick ring — CCW */}
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
        {/* crosshair */}
        <g className="reactor-cross">
          <line x1="100" y1="14" x2="100" y2="34" />
          <line x1="100" y1="166" x2="100" y2="186" />
          <line x1="14" y1="100" x2="34" y2="100" />
          <line x1="166" y1="100" x2="186" y2="100" />
        </g>
        {/* inner core */}
        <circle className="reactor-core-ring" cx="100" cy="100" r="34" />
      </svg>

      <div className="reactor-core" />
      <div className="reactor-glow" />
      <div className="reactor-status">{p.label}</div>
    </div>
  );
}
