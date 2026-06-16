import '../styles/addons.css';
import { useEffect, useRef } from 'react';
import type { AuriState } from '../lib/auriState';
import { prefersReducedMotion } from '../lib/webgl';
import {
  ACTIONS,
  DOCR,
  LINES_DOCR,
  LINES_TRAVELLER,
  TRAVELLER,
  WEIGHTS_DOCR,
  WEIGHTS_TRAVELLER,
  drawCharacter,
  pickAction,
  type Action,
  type CharDef,
} from '../lib/residents';

interface Props {
  state: AuriState;
  enabled: boolean;
}

interface Actor {
  def: CharDef;
  weights: Record<string, number>;
  lines: string[];
  x: number;
  facing: 1 | -1;
  action: Action;
  elapsed: number;
  forced: boolean;
  bubble: { text: string; until: number } | null;
}

type Interaction = { type: 'talk' | 'chase'; until: number; nextSpeak: number; speaker: 0 | 1 } | null;

const S = 3.5; // pixel scale
const PROXIMITY = 110;

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  if (typeof ctx.roundRect === 'function') {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  } else {
    ctx.beginPath();
    ctx.rect(x, y, w, h);
  }
}

function drawBubble(ctx: CanvasRenderingContext2D, text: string, cx: number, topY: number) {
  const fs = 12;
  ctx.font = `${fs}px 'Share Tech Mono', monospace`;
  const padX = 7;
  const padY = 5;
  const w = ctx.measureText(text).width + padX * 2;
  const h = fs + padY * 2;
  const x = cx - w / 2;
  const y = topY - h - 8;
  ctx.fillStyle = 'rgba(8,20,30,0.88)';
  ctx.strokeStyle = 'rgba(31,229,255,0.6)';
  ctx.lineWidth = 1;
  roundRect(ctx, x, y, w, h, 4);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = 'rgba(8,20,30,0.88)';
  ctx.fillRect(cx - 3, y + h - 1, 6, 5);
  ctx.fillStyle = '#cdeefe';
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  ctx.fillText(text, x + padX, y + padY);
}

// Bottom-strip pixel "residents": two original parody figures that wander,
// goof around, occasionally chat, and react to Auri's state. Transparent layer,
// pointer-events:none — never interferes with the chat or the 3D core.
export default function Residents({ state, enabled }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  const enabledRef = useRef(enabled);
  stateRef.current = state;
  enabledRef.current = enabled;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf = 0;
    let last = performance.now();
    let width = 0;
    let height = 0;
    let groundY = 0;
    const dpr = Math.min(2, window.devicePixelRatio || 1);

    const resize = () => {
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = false;
      groundY = height - 8;
    };
    resize();

    const actors: Actor[] = [
      { def: DOCR, weights: WEIGHTS_DOCR, lines: LINES_DOCR, x: width * 0.32, facing: 1, action: ACTIONS.idle, elapsed: 0, forced: false, bubble: null },
      { def: TRAVELLER, weights: WEIGHTS_TRAVELLER, lines: LINES_TRAVELLER, x: width * 0.6, facing: -1, action: ACTIONS.idle, elapsed: 0, forced: false, bubble: null },
    ];
    let interaction: Interaction = null;
    let cooldown = 2;

    const xMin = () => 30;
    const xMax = () => Math.max(60, width - 30);

    const endAction = (a: Actor) => {
      a.elapsed = 0;
      a.forced = false;
      a.action = pickAction(a.weights);
      if (a.action.name === 'walk') a.facing = Math.random() < 0.5 ? 1 : -1;
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      ctx.clearRect(0, 0, width, height);
      if (!enabledRef.current) return;

      const reduced = prefersReducedMotion();
      const reacting = stateRef.current === 'thinking' || stateRef.current === 'speaking';
      const nowS = now / 1000;
      cooldown -= dt;

      // ── Auri reaction takes priority: face inward and point/wave at the core
      if (reacting && !reduced) {
        interaction = null;
        const react = stateRef.current === 'thinking' ? ACTIONS.point : ACTIONS.wave;
        for (const a of actors) {
          a.facing = a.x < width / 2 ? 1 : -1;
          if (a.action !== react) {
            a.action = react;
            a.elapsed = 0;
          }
          a.forced = true;
        }
      }

      // ── maybe start an interaction when both are free and close
      if (!reacting && !reduced && !interaction && cooldown <= 0) {
        const dist = Math.abs(actors[0].x - actors[1].x);
        if (dist < PROXIMITY && Math.random() < 0.5) {
          const type = Math.random() < 0.25 ? 'chase' : 'talk';
          interaction = { type, until: nowS + (type === 'chase' ? 2.6 : 4.6), nextSpeak: nowS, speaker: 0 };
          cooldown = 8;
        } else {
          cooldown = 2.5;
        }
      }

      // ── interaction handling
      if (interaction && !reacting) {
        const [a0, a1] = actors;
        if (interaction.type === 'talk') {
          a0.facing = a0.x < a1.x ? 1 : -1;
          a1.facing = a1.x < a0.x ? 1 : -1;
          for (const a of actors) {
            a.forced = true;
            if (a.action !== ACTIONS.idle && a.action !== ACTIONS.laugh) {
              a.action = ACTIONS.idle;
              a.elapsed = 0;
            }
          }
          if (nowS >= interaction.nextSpeak) {
            const sp = actors[interaction.speaker];
            sp.bubble = { text: sp.lines[Math.floor(Math.random() * sp.lines.length)], until: nowS + 1.8 };
            sp.action = ACTIONS.laugh;
            sp.elapsed = 0;
            interaction.speaker = interaction.speaker === 0 ? 1 : 0;
            interaction.nextSpeak = nowS + 1.6;
          }
        } else {
          // chase: actor 0 walks toward actor 1
          const dir: 1 | -1 = a0.x < a1.x ? 1 : -1;
          a0.facing = dir;
          a0.action = ACTIONS.walk;
          a0.forced = true;
          a0.x += dir * 46 * dt;
          a1.facing = dir;
          a1.action = ACTIONS.walk;
          a1.forced = true;
          a1.x += dir * 40 * dt;
        }
        if (nowS >= interaction.until) {
          for (const a of actors) a.forced = false;
          interaction = null;
        }
      }

      // ── per-actor update + draw
      for (const a of actors) {
        a.elapsed += dt;

        if (reduced) {
          a.action = ACTIONS.idle;
        } else if (a.action.speed && !a.forced) {
          a.x += a.facing * a.action.speed * dt;
        }

        if (a.x < xMin()) {
          a.x = xMin();
          a.facing = 1;
        } else if (a.x > xMax()) {
          a.x = xMax();
          a.facing = -1;
        }

        if (a.elapsed >= a.action.dur) {
          if (a.forced) a.elapsed = 0;
          else endAction(a);
        }

        if (a.bubble && nowS > a.bubble.until) a.bubble = null;

        const prog = Math.min(1, a.elapsed / a.action.dur);
        const pose = a.action.pose(prog);

        // soft glow under the feet
        ctx.save();
        ctx.fillStyle = a.def.glow;
        ctx.beginPath();
        ctx.ellipse(a.x, groundY + 2, 16, 5, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        drawCharacter(ctx, a.def, pose, a.x, groundY, S, a.facing);
        a.action.fx?.(ctx, a.x, groundY, S, a.facing, prog);

        if (a.bubble) drawBubble(ctx, a.bubble.text, a.x, groundY - 16 * S);
      }
    };

    raf = requestAnimationFrame(frame);
    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="residents-canvas" aria-hidden="true" />;
}
