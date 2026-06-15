// Parametric pixel-art "residents" for the HUD.
//
// COPYRIGHT NOTE: DOC-R and THE TRAVELLER are ORIGINAL parody pixel figures,
// only loosely *inspired* by archetypes (a manic scientist / a cryptic traveller).
// No official names, logos, likenesses or copied sprites are used.
//
// Each figure is drawn parametrically from a small set of pose parameters, so a
// handful of actions produce many readable little animations without hand-
// drawing hundreds of frames.

export type ArmPos = 'down' | 'out' | 'up' | 'head' | 'fore';

export interface Pose {
  bob: number; // vertical offset (px, negative = up)
  step: number; // -1..1 leg swing
  armL: ArmPos;
  armR: ArmPos;
  lean: number; // -1..1 tilt
  prop?: boolean; // show gadget near right hand
  blink?: boolean;
  sit?: boolean;
}

export interface CharDef {
  name: string;
  hair: string;
  hair2: string;
  coat: string;
  shirt: string;
  skin: string;
  pants: string;
  spiky: boolean;
  glow: string;
}

export const DOCR: CharDef = {
  name: 'DOC-R',
  hair: '#eef2f5',
  hair2: '#cdd6db',
  coat: '#eef1f4',
  shirt: '#3a6ea5',
  skin: '#e7b48a',
  pants: '#2b3b46',
  spiky: true,
  glow: 'rgba(120,220,255,0.5)',
};

export const TRAVELLER: CharDef = {
  name: 'TRAVELLER',
  hair: '#d4d8db',
  hair2: '#a9b0b4',
  coat: '#5b1f2a',
  shirt: '#2a2f36',
  skin: '#e7b48a',
  pants: '#22262c',
  spiky: false,
  glow: 'rgba(255,120,90,0.45)',
};

const GW = 10; // grid width in cells
const GH = 16; // grid height in cells

const stand = (over: Partial<Pose> = {}): Pose => ({
  bob: 0,
  step: 0,
  armL: 'down',
  armR: 'down',
  lean: 0,
  ...over,
});

/** Draw one character. (cx, groundY) is the feet anchor on the canvas. */
export function drawCharacter(
  ctx: CanvasRenderingContext2D,
  def: CharDef,
  pose: Pose,
  cx: number,
  groundY: number,
  S: number,
  facing: 1 | -1,
): void {
  const ox = Math.round(cx - (GW / 2) * S);
  const oy = Math.round(groundY - GH * S + pose.bob);
  const lean = pose.lean || 0;

  const px = (gx: number, gy: number, w: number, h: number, color: string | null) => {
    if (!color) return;
    const mgx = facing < 0 ? GW - gx - w : gx;
    const shift = Math.round(lean * (1 - gy / GH) * 2) * facing;
    ctx.fillStyle = color;
    ctx.fillRect(ox + mgx * S + shift * S, oy + gy * S, w * S, h * S);
  };

  const arm = (pos: ArmPos, side: 'L' | 'R') => {
    const x = side === 'L' ? 2 : 7;
    switch (pos) {
      case 'up':
        px(x, 2, 1, 4, def.coat);
        px(x, 1, 1, 1, def.skin);
        break;
      case 'out':
        px(side === 'L' ? 0 : 8, 6, 2, 1, def.coat);
        break;
      case 'head':
        px(x, 4, 1, 2, def.coat);
        px(side === 'L' ? 3 : 6, 3, 1, 1, def.skin);
        break;
      case 'fore':
        px(side === 'L' ? 1 : 8, 7, 2, 1, def.coat);
        px(side === 'L' ? 0 : 9, 7, 1, 1, def.skin);
        if (pose.prop && side === 'R') px(facing < 0 ? -1 : 10, 6, 1, 2, '#9be7ff');
        break;
      case 'down':
      default:
        px(x, 6, 1, 5, def.coat);
        px(x, 11, 1, 1, def.skin);
    }
  };

  // legs / sitting
  if (pose.sit) {
    px(3, 12, 2, 2, def.pants);
    px(5, 12, 2, 2, def.pants);
    px(2, 13, 1, 1, def.pants);
    px(7, 13, 1, 1, def.pants);
  } else {
    const sw = pose.step;
    px(3, 12, 2, 4, def.pants);
    px(5, 12, 2, 4, def.pants);
    px(3 + (sw < -0.3 ? -1 : 0), 15, 2, 1, '#16191d');
    px(5 + (sw > 0.3 ? 1 : 0), 15, 2, 1, '#16191d');
  }

  // torso + shirt
  px(3, 6, 4, 6, def.coat);
  px(4, 7, 2, 4, def.shirt);

  // arms
  arm(pose.armL, 'L');
  arm(pose.armR, 'R');

  // head + eyes
  px(3, 2, 4, 4, def.skin);
  if (!pose.blink) {
    px(4, 4, 1, 1, '#21262c');
    px(6, 4, 1, 1, '#21262c');
  } else {
    px(4, 4, 3, 1, '#21262c');
  }

  // hair
  if (def.spiky) {
    px(3, 1, 4, 1, def.hair);
    px(2, 1, 1, 1, def.hair);
    px(7, 1, 1, 1, def.hair);
    px(3, 0, 1, 1, def.hair);
    px(5, 0, 1, 1, def.hair);
    px(6, 0, 1, 1, def.hair);
    px(4, 1, 1, 1, def.hair2);
  } else {
    px(2, 1, 6, 2, def.hair);
    px(2, 3, 1, 1, def.hair2);
    px(7, 3, 1, 1, def.hair2);
    px(3, 0, 4, 1, def.hair2);
  }
}

// ── actions ──────────────────────────────────────────────────────────────────
export interface Action {
  name: string;
  dur: number; // seconds
  speed: number; // px/sec horizontal movement
  pose: (t: number) => Pose; // t in 0..1
}

export const ACTIONS: Record<string, Action> = {
  idle: { name: 'idle', dur: 2.2, speed: 0, pose: (t) => stand({ bob: Math.sin(t * Math.PI * 2) * 0.5, blink: t > 0.46 && t < 0.52 }) },
  walk: {
    name: 'walk',
    dur: 3,
    speed: 24,
    pose: (t) => {
      const ph = t * Math.PI * 2 * 4;
      return stand({
        step: Math.sin(ph),
        bob: -Math.abs(Math.sin(ph)) * 0.6,
        armL: Math.sin(ph) > 0 ? 'fore' : 'down',
        armR: Math.sin(ph) < 0 ? 'fore' : 'down',
      });
    },
  },
  wave: { name: 'wave', dur: 1.5, speed: 0, pose: (t) => stand({ armR: Math.sin(t * Math.PI * 8) > 0 ? 'up' : 'out', bob: Math.sin(t * Math.PI * 2) * 0.3 }) },
  jump: { name: 'jump', dur: 0.9, speed: 0, pose: (t) => stand({ bob: -Math.sin(t * Math.PI) * 7, armL: 'up', armR: 'up' }) },
  think: { name: 'think', dur: 2.4, speed: 0, pose: (t) => stand({ armR: 'head', bob: Math.sin(t * Math.PI * 2) * 0.3 }) },
  laugh: { name: 'laugh', dur: 1.4, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI * 10) * 0.4, bob: -Math.abs(Math.sin(t * Math.PI * 5)) }) },
  trip: { name: 'trip', dur: 1.0, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI) * 1.3, bob: -Math.sin(t * Math.PI) * 2, step: t < 0.5 ? 1 : -1, armL: 'out', armR: 'out' }) },
  point: { name: 'point', dur: 1.5, speed: 0, pose: (t) => stand({ armR: 'fore', bob: Math.sin(t * Math.PI * 2) * 0.2 }) },
  gadget: { name: 'gadget', dur: 1.8, speed: 0, pose: (t) => stand({ armR: 'fore', prop: true, blink: Math.sin(t * Math.PI * 12) > 0 }) },
  sit: { name: 'sit', dur: 2.8, speed: 0, pose: () => stand({ bob: 4, sit: true }) },
  dance: {
    name: 'dance',
    dur: 1.8,
    speed: 0,
    pose: (t) => {
      const ph = t * Math.PI * 8;
      return stand({ lean: Math.sin(ph) * 0.6, bob: -Math.abs(Math.sin(ph)) * 1.5, armL: Math.sin(ph) > 0 ? 'up' : 'out', armR: Math.sin(ph) < 0 ? 'up' : 'out' });
    },
  },
  glitch: { name: 'glitch', dur: 0.7, speed: 0, pose: (t) => stand({ lean: (Math.random() - 0.5) * 2, bob: (Math.random() - 0.5) * 4, blink: t > 0.3 }) },
};

// Per-character action weights (DOC-R is goofier; THE TRAVELLER calmer).
export const WEIGHTS_DOCR: Record<string, number> = {
  idle: 4, walk: 5, wave: 2, jump: 3, think: 1, laugh: 3, trip: 2, point: 2, gadget: 3, sit: 1, dance: 2, glitch: 1,
};
export const WEIGHTS_TRAVELLER: Record<string, number> = {
  idle: 5, walk: 5, wave: 2, jump: 1, think: 4, laugh: 1, trip: 1, point: 3, gadget: 2, sit: 2, dance: 1, glitch: 1,
};

export function pickAction(weights: Record<string, number>): Action {
  const entries = Object.entries(weights);
  const total = entries.reduce((s, [, w]) => s + w, 0);
  let r = Math.random() * total;
  for (const [name, w] of entries) {
    r -= w;
    if (r <= 0) return ACTIONS[name];
  }
  return ACTIONS.idle;
}

// Original, harmless, parody one-liners (Hungarian). Not quotes from any show.
export const LINES_DOCR = [
  'A tudomány nem kér bocsánatot.',
  'Ezt elronthatjuk — de stílusosan.',
  'Hol a kávém? És a józan eszem?',
  'Számoltam. A válasz: hát, kábé.',
  'Ne pislogj, lemaradsz a zsenialitásról.',
  'Ez vagy működik, vagy tanulságos.',
  'Adj egy hétvégét és egy reaktort.',
];
export const LINES_TRAVELLER = [
  'Érdekes. Folytasd.',
  'Az idő már csak ilyen szeszélyes.',
  'Láttam furcsábbat is. Kedden.',
  'Minden ajtó mögött egy másik ajtó.',
  'Semmi pánik — az az én reszortom.',
  'A válasz a kérdésben bujkál.',
  'A téblábolás is utazás.',
];

export { GW, GH };
