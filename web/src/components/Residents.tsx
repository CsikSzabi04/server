import '../styles/addons.css';
import { useEffect, useRef } from 'react';
import type { AuriState } from '../lib/auriState';
import { prefersReducedMotion } from '../lib/webgl';
import {
  ACTIONS,
  ARGUE_LINES,
  DOCR,
  LINES_DOCR,
  LINES_TRAVELLER,
  TRAVELLER_FORMS,
  WEIGHTS_DOCR,
  WEIGHTS_TRAVELLER,
  drawCharacter,
  drawNotes,
  drawPortal,
  drawShootingStar,
  drawSmoke,
  drawSpark,
  drawVisitor,
  pickAction,
  type Action,
  type ActorLike,
  type CharDef,
  type VisitorKind,
  type WorldLike,
} from '../lib/residents';

interface Props {
  state: AuriState;
  enabled: boolean;
}

interface Actor extends ActorLike {
  forms: CharDef[];
  weights: Record<string, number>;
  lines: string[];
  action: Action;
  elapsed: number;
  nextEvent: number; // index of the action's next one-shot event
  forced: boolean; // a scene / Auri reaction is driving this actor
  fade: number; // scene-controlled opacity (portal swap)
  vis: number; // final opacity this frame
  bubble: { text: string; until: number } | null;
}

/** Something that shows up for a few seconds: wanders, or tags along behind an actor. */
interface Visitor {
  kind: VisitorKind;
  x: number;
  dir: 1 | -1;
  age: number;
  life: number;
  follow: Actor | null;
}

type SceneType = 'talk' | 'argue' | 'chase' | 'highFive' | 'danceOff' | 'flee' | 'portalSwap' | 'stargaze' | 'race';
/** A joint scene: both residents (or one, for `flee`) are scripted until it ends. */
interface Scene {
  type: SceneType;
  t: number;
  dur: number;
  step: number;
  mark: number;
  meet: number;
  who: 0 | 1;
  dir: 1 | -1;
  speeds: [number, number];
  visitor: Visitor | null;
  banter: [string, string];
}

const S = 3.5; // pixel scale
const PROXIMITY = 110;
const MAX_VISITORS = 3;
const VISITOR_SPEED: Record<VisitorKind, number> = { dino: 46, drone: 30, saucer: 34, duck: 32, blob: 40 };
const SCENE_DUR: Record<SceneType, number> = {
  talk: 4.6,
  argue: 5.6,
  chase: 2.6,
  highFive: 9,
  danceOff: 6.4,
  flee: 30,
  portalSwap: 4.4,
  stargaze: 6.6,
  race: 9,
};

const pickOne = <T,>(arr: readonly T[]): T => arr[Math.floor(Math.random() * arr.length)];
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const ramp = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));

function weighted<T extends string>(w: Partial<Record<T, number>>): T | null {
  const entries = Object.entries(w) as [T, number][];
  let r = Math.random() * entries.reduce((s, [, v]) => s + v, 0);
  for (const [k, v] of entries) {
    r -= v;
    if (r <= 0) return k;
  }
  return entries[0]?.[0] ?? null;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  if (typeof ctx.roundRect === 'function') {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  } else {
    ctx.beginPath();
    ctx.rect(x, y, w, h);
  }
}

function drawBubble(ctx: CanvasRenderingContext2D, text: string, cx: number, topY: number, viewW: number) {
  const fs = 12;
  ctx.font = `${fs}px 'Share Tech Mono', monospace`;
  const padX = 7;
  const padY = 5;
  const w = ctx.measureText(text).width + padX * 2;
  const h = fs + padY * 2;
  const x = Math.max(4, Math.min(viewW - w - 4, cx - w / 2)); // keep it on screen
  const y = topY - h - 8;
  ctx.fillStyle = 'rgba(8,20,30,0.88)';
  ctx.strokeStyle = 'rgba(31,229,255,0.6)';
  ctx.lineWidth = 1;
  roundRect(ctx, x, y, w, h, 4);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = 'rgba(8,20,30,0.88)';
  ctx.fillRect(Math.max(x + 3, Math.min(x + w - 9, cx - 3)), y + h - 1, 6, 5);
  ctx.fillStyle = '#cdeefe';
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  ctx.fillText(text, x + padX, y + padY);
}

// Bottom-strip pixel "residents": two original parody figures that wander, goof
// around, play joint scenes (banter, high-five, dance-off, races, stargazing, portal
// pranks), get visited by odd critters, and react to Auri's state. The Traveller
// sometimes takes his time capsule and comes back in a different (original) look.
// Transparent layer, pointer-events:none — never interferes with the chat or the core.
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

    const mkActor = (forms: CharDef[], weights: Record<string, number>, lines: string[], x: number, facing: 1 | -1): Actor => ({
      def: forms[0],
      forms,
      formIdx: 0,
      weights,
      lines,
      x,
      facing,
      action: ACTIONS.idle,
      elapsed: 0,
      nextEvent: 0,
      forced: false,
      fade: 1,
      vis: 1,
      bubble: null,
    });
    const actors: [Actor, Actor] = [
      mkActor([DOCR], WEIGHTS_DOCR, LINES_DOCR, width * 0.32, 1),
      mkActor(TRAVELLER_FORMS, WEIGHTS_TRAVELLER, LINES_TRAVELLER, width * 0.6, -1),
    ];
    const visitors: Visitor[] = [];
    let scene: Scene | null = null;
    let cooldown = 3;
    let ambient = 40 + Math.random() * 40;
    let clock = 0;
    let reducedNow = false;
    let reactingNow = false;
    let wasReacting = false;

    const xMin = () => 30;
    const xMax = () => Math.max(60, width - 30);
    const clampX = (x: number) => Math.max(xMin(), Math.min(xMax(), x));

    const setAction = (a: Actor, act: Action) => {
      if (a.action === act) return;
      a.action = act;
      a.elapsed = 0;
      a.nextEvent = 0;
    };
    const endAction = (a: Actor) => {
      a.elapsed = 0;
      a.nextEvent = 0;
      a.forced = false;
      a.action = reducedNow ? ACTIONS.idle : pickAction(a.weights);
      if (a.action.speed) a.facing = Math.random() < 0.5 ? 1 : -1;
    };
    const say = (a: Actor, text: string, secs = 1.8) => {
      a.bubble = { text, until: clock + secs };
    };
    /** Walk an actor toward x; true once it's there. */
    const approach = (a: Actor, tx: number, speed: number, dt: number): boolean => {
      const d = clampX(tx) - a.x;
      if (Math.abs(d) < 2) {
        setAction(a, ACTIONS.idle);
        return true;
      }
      a.facing = d > 0 ? 1 : -1;
      a.x += Math.sign(d) * Math.min(Math.abs(d), speed * dt);
      setAction(a, ACTIONS.walk);
      return false;
    };
    const faceEachOther = () => {
      const d: 1 | -1 = actors[0].x <= actors[1].x ? 1 : -1;
      actors[0].facing = d;
      actors[1].facing = d === 1 ? -1 : 1;
    };
    const isFree = (a: Actor) => !a.forced && !a.action.alpha && a.fade >= 1;

    const endScene = () => {
      for (const a of actors) {
        a.forced = false;
        a.fade = 1;
      }
      scene = null;
      cooldown = 7 + Math.random() * 5;
    };
    const newScene = (type: SceneType): Scene => ({
      type,
      t: 0,
      dur: SCENE_DUR[type],
      step: 0,
      mark: 0,
      meet: (actors[0].x + actors[1].x) / 2,
      who: 0,
      dir: 1,
      speeds: [60 + Math.random() * 14, 60 + Math.random() * 14],
      visitor: null,
      banter: pickOne(ARGUE_LINES),
    });
    const startScene = (type: SceneType) => {
      const sc = newScene(type);
      if (type === 'race') sc.dir = sc.meet < width / 2 ? 1 : -1;
      scene = sc;
      for (const a of actors) a.forced = true;
    };
    const startFlee = (a: Actor, v: Visitor) => {
      const sc = newScene('flee');
      sc.who = a === actors[0] ? 0 : 1;
      sc.dir = a.x >= v.x ? 1 : -1;
      sc.visitor = v;
      scene = sc;
      a.forced = true;
    };

    const world: WorldLike = {
      get width() {
        return width;
      },
      randomX(avoid) {
        const lo = xMin();
        const hi = xMax();
        for (let i = 0; i < 10; i++) {
          const x = lo + Math.random() * (hi - lo);
          if (avoid === undefined || Math.abs(x - avoid) > Math.min(160, (hi - lo) / 3)) return x;
        }
        return lo + Math.random() * (hi - lo);
      },
      spawn(kind, x, dir, opts) {
        if (reducedNow || visitors.length >= MAX_VISITORS) return;
        const follow = (actors as Actor[]).find((a) => a === opts?.follow) ?? null;
        const v: Visitor = { kind, x: clampX(x), dir, age: 0, life: opts?.life ?? 6, follow };
        visitors.push(v);
        // something scary turned up: whoever is standing around runs for it
        if (!follow && (kind === 'dino' || kind === 'drone') && !scene && !reactingNow && Math.random() < 0.7) {
          const target = actors.find((a) => a.vis > 0.9 && isFree(a));
          if (target) {
            v.follow = target;
            v.life = Math.max(v.life, 6);
            startFlee(target, v);
          }
        }
        if (opts?.say && follow) say(follow, opts.say);
      },
      say(a, text, secs) {
        say(a as Actor, text, secs);
      },
    };

    // ── joint scenes ──────────────────────────────────────────────────────────
    const runScene = (sc: Scene, dt: number) => {
      sc.t += dt;
      const t = sc.t;
      const [a0, a1] = actors;
      switch (sc.type) {
        case 'talk': {
          faceEachOther();
          if (t >= sc.mark) {
            const sp = actors[sc.who];
            say(sp, pickOne(sp.lines), 1.8);
            setAction(sp, ACTIONS.laugh);
            setAction(actors[sc.who === 0 ? 1 : 0], ACTIONS.idle);
            sc.who = sc.who === 0 ? 1 : 0;
            sc.mark = t + 1.6;
          }
          break;
        }
        case 'argue': {
          faceEachOther();
          if (sc.step === 0) {
            say(a0, sc.banter[0], 1.9);
            setAction(a0, ACTIONS.point);
            setAction(a1, ACTIONS.idle);
            sc.step = 1;
          } else if (sc.step === 1 && t >= 1.9) {
            say(a1, sc.banter[1], 2.1);
            setAction(a1, ACTIONS.point);
            setAction(a0, ACTIONS.shrug);
            sc.step = 2;
          } else if (sc.step === 2 && t >= 4.1) {
            setAction(a0, ACTIONS.facepalm);
            setAction(a1, ACTIONS.laugh);
            sc.step = 3;
          }
          break;
        }
        case 'chase': {
          const dir: 1 | -1 = a0.x < a1.x ? 1 : -1;
          a0.facing = dir;
          a1.facing = dir;
          setAction(a0, ACTIONS.walk);
          setAction(a1, ACTIONS.walk);
          a0.x += dir * 46 * dt;
          a1.x += dir * 40 * dt;
          if (sc.step === 0) {
            say(a1, pickOne(['Not again!', 'Catch me if you can!']), 1.4);
            sc.step = 1;
          }
          break;
        }
        case 'highFive': {
          if (sc.step === 0) {
            const l = a0.x <= a1.x ? a0 : a1;
            const r = l === a0 ? a1 : a0;
            const okL = approach(l, sc.meet - 11, 42, dt);
            const okR = approach(r, sc.meet + 11, 42, dt);
            if ((okL && okR) || t > 4) {
              l.facing = 1;
              r.facing = -1;
              setAction(a0, ACTIONS.highFive);
              setAction(a1, ACTIONS.highFive);
              sc.meet = (l.x + r.x) / 2;
              sc.step = 1;
              sc.mark = t;
            }
          } else if (sc.step === 1 && t - sc.mark >= 0.9) {
            setAction(a0, ACTIONS.cheer);
            setAction(a1, ACTIONS.cheer);
            say(a0, pickOne(['Up top!', 'Science five!']), 1.4);
            say(a1, pickOne(['Splendid!', 'Five, across time!']), 1.4);
            sc.step = 2;
            sc.mark = t;
          } else if (sc.step === 2 && t - sc.mark >= 1.3) {
            sc.dur = t;
          }
          break;
        }
        case 'danceOff': {
          faceEachOther();
          if (t < 2) {
            setAction(a0, ACTIONS.dance);
            setAction(a1, ACTIONS.idle);
          } else if (t < 4) {
            setAction(a1, ACTIONS.dance);
            setAction(a0, ACTIONS.idle);
          } else {
            setAction(a0, ACTIONS.dance);
            setAction(a1, ACTIONS.dance);
          }
          if (sc.step === 0) {
            say(a0, 'Dance-off!', 1.4);
            sc.step = 1;
          } else if (sc.step === 1 && t > 2.05) {
            say(a1, pickOne(['Observe. Vintage moves.', 'From the 2380s.']), 1.6);
            sc.step = 2;
          } else if (sc.step === 2 && t > 5.4) {
            say(a1, pickOne(['A draw, I think.', 'I win. Obviously.']), 1.4);
            sc.step = 3;
          }
          break;
        }
        case 'flee': {
          const a = actors[sc.who];
          const v = sc.visitor;
          if (!v || !visitors.includes(v)) {
            say(a, pickOne(['Is it gone?', 'Phew.', "…I wasn't scared."]), 1.6);
            setAction(a, ACTIONS.shrug);
            sc.dur = t;
            break;
          }
          setAction(a, ACTIONS.flee);
          a.facing = sc.dir;
          a.x += sc.dir * 58 * dt;
          if (a.x <= xMin() + 1) sc.dir = 1;
          if (a.x >= xMax() - 1) sc.dir = -1;
          if (sc.step === 0) {
            say(a, pickOne(a === a0 ? ['NOPE.', 'Not today!', 'Who invited THAT?'] : ['Oh dear.', 'Not this again!', 'Shoo! Shoo!']), 1.5);
            sc.step = 1;
          }
          break;
        }
        case 'portalSwap': {
          // DOC-R zaps the Traveller through a portal to somewhere else on the strip
          if (sc.step === 0) {
            a0.facing = a0.x <= a1.x ? 1 : -1;
            setAction(a0, ACTIONS.portalGun);
            setAction(a1, ACTIONS.idle);
            say(a0, pickOne(['Hold still.', 'Trust me!', 'Quick experiment…']), 1.3);
            sc.step = 1;
          } else if (sc.step === 1 && t >= 0.9) {
            sc.meet = a1.x;
            setAction(a1, ACTIONS.trip);
            sc.step = 2;
          } else if (sc.step === 2 && t >= 1.5) {
            a1.x = world.randomX(a1.x);
            sc.mark = a1.x;
            setAction(a1, ACTIONS.idle);
            sc.step = 3;
          } else if (sc.step === 3 && t >= 2.1) {
            a1.facing = a1.x <= a0.x ? 1 : -1;
            setAction(a1, ACTIONS.facepalm);
            setAction(a0, ACTIONS.laugh);
            say(a1, pickOne(['Rude.', 'I had a schedule!', 'Was that necessary?']), 1.6);
            sc.step = 4;
          }
          a1.fade = t < 1.5 ? 1 - ramp(t, 1.0, 1.4) : ramp(t, 1.6, 2.0);
          break;
        }
        case 'stargaze': {
          faceEachOther();
          setAction(a0, ACTIONS.sit);
          setAction(a1, ACTIONS.sit);
          if (sc.step === 0 && t >= 0.3) {
            say(a1, 'Look up.', 1.3);
            sc.step = 1;
          } else if (sc.step === 1 && t >= 2.2) {
            say(a1, 'Make a wish.', 1.5);
            sc.step = 2;
          } else if (sc.step === 2 && t >= 3.8) {
            say(a0, pickOne(['More portal fluid.', 'Infinite snacks.', 'A nap. A long one.']), 1.6);
            sc.step = 3;
          } else if (sc.step === 3 && t >= 5.4) {
            say(a1, "Mine's a secret.", 1.2);
            sc.step = 4;
          }
          break;
        }
        case 'race': {
          if (sc.step === 0) {
            say(a1, 'Race you!', 1.2);
            sc.mark = t + 0.7;
            sc.step = 1;
          }
          if (sc.step === 1) {
            for (const a of actors) {
              a.facing = sc.dir;
              setAction(a, ACTIONS.idle);
            }
            if (t >= sc.mark) sc.step = 2;
          } else if (sc.step === 2) {
            actors.forEach((a, i) => {
              a.facing = sc.dir;
              setAction(a, ACTIONS.run);
              a.x += sc.dir * (sc.speeds[i] + Math.sin(t * 5 + i * 2) * 8) * dt;
            });
            const atWall = actors.some((a) => a.x <= xMin() + 1 || a.x >= xMax() - 1);
            if (atWall || t > 4.2) {
              const winner = sc.dir > 0 ? (a0.x >= a1.x ? a0 : a1) : a0.x <= a1.x ? a0 : a1;
              const loser = winner === a0 ? a1 : a0;
              setAction(winner, ACTIONS.cheer);
              setAction(loser, ACTIONS.facepalm);
              say(winner, winner === a0 ? 'Ha! Science!' : 'Practice. Centuries of it.', 1.5);
              sc.dur = t + 1.6;
              sc.step = 3;
            }
          }
          break;
        }
      }
      if (sc.t >= sc.dur) endScene();
    };

    const drawSceneFx = (sc: Scene) => {
      const t = sc.t;
      if (sc.type === 'highFive' && sc.step === 1) {
        const k = (t - sc.mark) / 0.9;
        if (k > 0.35) drawSpark(ctx, sc.meet, groundY - 15.5 * S, S, 1 - (k - 0.35) / 0.65);
      } else if (sc.type === 'danceOff') {
        for (const a of actors) if (a.action === ACTIONS.dance) drawNotes(ctx, a.x, groundY, S, t);
      } else if (sc.type === 'portalSwap') {
        const r = 3.2 * S;
        if (t > 0.8 && t < 1.6) drawPortal(ctx, sc.meet, groundY - 7 * S, r * Math.min(ramp(t, 0.8, 1.0), 1 - ramp(t, 1.4, 1.6)), t);
        if (t > 1.5 && t < 2.4) drawPortal(ctx, sc.mark, groundY - 7 * S, r * Math.min(ramp(t, 1.5, 1.7), 1 - ramp(t, 2.1, 2.4)), t);
      } else if (sc.type === 'stargaze') {
        drawShootingStar(ctx, width, groundY, S, (t - 1.4) / 1.8);
      }
    };

    // ── visitors ──────────────────────────────────────────────────────────────
    const updateVisitors = (dt: number) => {
      for (let i = visitors.length - 1; i >= 0; i--) {
        const v = visitors[i];
        v.age += dt;
        if (v.age >= v.life) {
          visitors.splice(i, 1);
          continue;
        }
        const sp = VISITOR_SPEED[v.kind];
        const f = v.follow;
        if (f && f.vis > 0.3) {
          // trail behind the actor (a saucer hovers right above instead)
          const tx = clampX(f.x - (v.kind === 'saucer' ? 0 : f.facing * 34));
          const d = tx - v.x;
          if (Math.abs(d) > 3) {
            v.dir = d > 0 ? 1 : -1;
            v.x += v.dir * Math.min(Math.abs(d), sp * dt);
          } else {
            v.dir = f.x >= v.x ? 1 : -1;
          }
        } else if (!f) {
          v.x += v.dir * sp * 0.6 * dt;
          if (v.x <= xMin()) v.dir = 1;
          if (v.x >= xMax()) v.dir = -1;
          v.x = clampX(v.x);
        }
        // (a follower whose actor is away just waits where it is)
      }
    };
    const drawVisitors = () => {
      for (const v of visitors) {
        const a = Math.min(1, v.age / 0.5, (v.life - v.age) / 0.6);
        drawVisitor(ctx, v.kind, v.x, groundY, S, v.dir, v.age, a);
        const py = v.kind === 'saucer' ? groundY - 26 * S : groundY - 4 * S;
        if (v.age < 0.6) drawSmoke(ctx, v.x, py, S, v.age / 0.6); // pops in…
        else if (v.age > v.life - 0.6) drawSmoke(ctx, v.x, py, S, 1 - (v.life - v.age) / 0.6); // …and out
      }
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      ctx.clearRect(0, 0, width, height);
      if (!enabledRef.current) return;

      clock += dt;
      reducedNow = prefersReducedMotion();
      reactingNow = !reducedNow && (stateRef.current === 'thinking' || stateRef.current === 'speaking');

      if (reducedNow) {
        visitors.length = 0;
        if (scene) endScene();
      }

      // ── Auri reaction takes priority: face inward and point/wave at the core
      if (reactingNow) {
        if (scene) endScene();
        const react = stateRef.current === 'thinking' ? ACTIONS.point : ACTIONS.wave;
        for (const a of actors) {
          if (!a.forced && a.action.alpha) continue; // let a vanishing trick finish first
          a.facing = a.x < width / 2 ? 1 : -1;
          setAction(a, react);
          a.forced = true;
        }
      } else if (wasReacting) {
        for (const a of actors) a.forced = false; // let them finish the wave, then carry on
      }
      wasReacting = reactingNow;

      // ── maybe start a joint scene when both are free
      cooldown -= dt;
      if (!reactingNow && !reducedNow && !scene && cooldown <= 0) {
        cooldown = 2.5;
        if (actors.every(isFree)) {
          const close = Math.abs(actors[0].x - actors[1].x) < PROXIMITY;
          if (Math.random() < (close ? 0.5 : 0.18)) {
            const type = weighted<SceneType>(
              close
                ? { talk: 3, argue: 2, highFive: 2, danceOff: 2, chase: 1, stargaze: 1, race: 1 }
                : { portalSwap: 2, highFive: 1, race: 1, stargaze: 1 },
            );
            if (type) startScene(type);
          }
        }
      }
      if (scene && !reactingNow) runScene(scene, dt);

      // ── now and then something just wanders across
      ambient -= dt;
      if (ambient <= 0) {
        ambient = 50 + Math.random() * 60;
        if (!reactingNow && !scene) {
          const dir: 1 | -1 = Math.random() < 0.5 ? 1 : -1;
          world.spawn(pickOne<VisitorKind>(['duck', 'saucer', 'blob']), dir > 0 ? xMin() : xMax(), dir, { life: 9 });
        }
      }
      updateVisitors(dt);

      // ── per-actor update
      for (const a of actors) {
        a.elapsed += dt;
        if (reducedNow) {
          setAction(a, ACTIONS.idle);
          a.fade = 1;
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

        // one-shot events (teleport, new form, a visitor, a line…)
        const evs = a.action.events;
        if (evs && !reducedNow) {
          const p = Math.min(1, a.elapsed / a.action.dur);
          while (a.nextEvent < evs.length && p >= evs[a.nextEvent].at) evs[a.nextEvent++].run(a, world);
        }

        if (a.elapsed >= a.action.dur) {
          if (a.forced) {
            a.elapsed = 0;
            a.nextEvent = 0;
          } else endAction(a);
        }
        if (a.bubble && clock > a.bubble.until) a.bubble = null;
      }

      // ── draw: visitors behind, then the residents, then scene effects and speech
      drawVisitors();
      for (const a of actors) {
        const prog = Math.min(1, a.elapsed / a.action.dur);
        const pose = a.action.pose(prog);
        a.vis = (a.action.alpha ? a.action.alpha(prog) : 1) * a.fade;

        if (a.vis > 0.02) {
          ctx.save();
          ctx.globalAlpha = a.vis;
          ctx.fillStyle = 'rgba(0,0,0,0.35)'; // contact shadow
          ctx.beginPath();
          ctx.ellipse(a.x, groundY + 1, 11, 3, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = a.def.glow; // soft glow under the feet
          ctx.beginPath();
          ctx.ellipse(a.x, groundY + 2, 16, 5, 0, 0, Math.PI * 2);
          ctx.fill();
          drawCharacter(ctx, a.def, pose, a.x, groundY, S, a.facing);
          ctx.restore();
        }
        a.action.fx?.(ctx, a.x, groundY, S, a.facing, prog, a.def);
      }
      if (scene) drawSceneFx(scene);
      // speech last; when both talk at once and the bubbles would overlap, stack them
      ctx.font = "12px 'Share Tech Mono', monospace";
      let prev: { x0: number; x1: number } | null = null;
      for (const a of actors) {
        if (!a.bubble || a.vis <= 0.3) continue;
        const w = ctx.measureText(a.bubble.text).width + 14;
        const x0 = Math.max(4, Math.min(width - w - 4, a.x - w / 2));
        const lift = prev && x0 < prev.x1 + 4 && x0 + w > prev.x0 - 4 ? 28 : 0;
        drawBubble(ctx, a.bubble.text, a.x, groundY - 16 * S - lift, width);
        prev = { x0, x1: x0 + w };
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
