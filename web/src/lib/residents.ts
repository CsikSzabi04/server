// Parametric pixel-art "residents" for the HUD.
//
// COPYRIGHT NOTE: DOC-R and THE TRAVELLER are ORIGINAL parody pixel figures,
// only loosely inspired by archetypes (a manic scientist / a time-travelling
// gentleman). No official sprites, logos or likenesses are copied; the props
// (portal gun, green portal, a blue box, a sonic tool) are generic sci-fi
// gadgets drawn from scratch, and the one-liners are short catchphrase-style
// quips. Each figure is drawn parametrically from a few pose parameters.

export type ArmPos = 'down' | 'out' | 'up' | 'head' | 'fore';

export interface Pose {
  bob: number; // vertical offset (px, negative = up)
  step: number; // -1..1 leg swing
  armL: ArmPos;
  armR: ArmPos;
  lean: number; // -1..1 tilt
  prop?: boolean; // small generic gadget in right hand
  blink?: boolean;
  sit?: boolean;
  scared?: boolean; // wide eyes + open mouth
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
  hair: '#9fe0f2', // blue hair
  hair2: '#5fb8d8',
  coat: '#eef1f4',
  shirt: '#3a6ea5',
  skin: '#e7b48a',
  pants: '#2b3b46',
  spiky: true,
  glow: 'rgba(120,255,150,0.45)',
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
  glow: 'rgba(120,200,255,0.45)',
};

const GW = 10;
const GH = 16;

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

  px(3, 6, 4, 6, def.coat);
  px(4, 7, 2, 4, def.shirt);

  arm(pose.armL, 'L');
  arm(pose.armR, 'R');

  // head + face
  px(3, 2, 4, 4, def.skin);
  if (pose.scared) {
    px(4, 4, 1, 1, '#21262c');
    px(6, 4, 1, 1, '#21262c');
    px(3, 3, 1, 1, '#21262c'); // raised brows
    px(7, 3, 1, 1, '#21262c');
    px(4, 5, 2, 1, '#1a1414'); // open mouth
  } else if (!pose.blink) {
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

// ── prop / effect drawers (smooth sci-fi over the blocky figures) ─────────────
function drawPortalGun(ctx: CanvasRenderingContext2D, hx: number, hy: number, S: number, f: 1 | -1): void {
  ctx.save();
  ctx.fillStyle = '#2c3138';
  ctx.fillRect(hx - 1.2 * S, hy - S, 2.4 * S, 1.8 * S);
  ctx.fillStyle = '#3a4047';
  ctx.fillRect(hx - 1.2 * S, hy - S, 2.4 * S, 0.5 * S);
  const bl = 1.8 * S;
  const bx = f > 0 ? hx + 1.0 * S : hx - 1.0 * S - bl;
  ctx.fillStyle = '#23272d';
  ctx.fillRect(bx, hy - 0.45 * S, bl, 0.9 * S);
  const tipX = f > 0 ? bx + bl : bx;
  const g = ctx.createRadialGradient(tipX, hy, 0, tipX, hy, 1.4 * S);
  g.addColorStop(0, 'rgba(150,255,140,0.9)');
  g.addColorStop(1, 'rgba(80,255,80,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(tipX, hy, 1.4 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#d6ffcf';
  ctx.beginPath();
  ctx.arc(tipX, hy, 0.35 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawPortal(ctx: CanvasRenderingContext2D, px: number, py: number, R: number, t: number): void {
  if (R < 0.5) return;
  ctx.save();
  ctx.translate(px, py);
  const glow = ctx.createRadialGradient(0, 0, 0, 0, 0, R * 1.5);
  glow.addColorStop(0, 'rgba(120,255,120,0.55)');
  glow.addColorStop(1, 'rgba(40,220,40,0)');
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.ellipse(0, 0, R * 1.3, R * 1.55, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = Math.max(1, R * 0.14);
  ctx.strokeStyle = '#9bff7a';
  for (let i = 0; i < 3; i++) {
    const a0 = (t * 6 + i * 1.2) % (Math.PI * 2);
    ctx.beginPath();
    ctx.ellipse(0, 0, R * (0.45 + i * 0.24), R * (0.55 + i * 0.24), 0, a0, a0 + 1.7 * Math.PI);
    ctx.stroke();
  }
  ctx.fillStyle = '#eaffea';
  ctx.beginPath();
  ctx.ellipse(0, 0, R * 0.22, R * 0.28, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawTentacles(
  ctx: CanvasRenderingContext2D,
  px: number,
  py: number,
  len: number,
  t: number,
  count: number,
  f: 1 | -1,
): void {
  ctx.save();
  ctx.strokeStyle = '#5fdc4a';
  ctx.lineWidth = Math.max(1.5, len * 0.06);
  ctx.lineCap = 'round';
  const baseAng = f > 0 ? Math.PI : 0; // reach back toward the character
  for (let i = 0; i < count; i++) {
    const spread = (i - (count - 1) / 2) * 0.5;
    let x = px;
    let y = py;
    ctx.beginPath();
    ctx.moveTo(x, y);
    const seg = len / 4;
    for (let s = 1; s <= 4; s++) {
      const ang = baseAng + spread + Math.sin(t * 9 + i * 1.3 + s) * 0.45;
      x += Math.cos(ang) * seg;
      y += Math.sin(ang) * seg;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = '#7dff66';
    ctx.beginPath();
    ctx.arc(x, y, len * 0.07, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawSonic(ctx: CanvasRenderingContext2D, hx: number, hy: number, S: number, f: 1 | -1, t: number): void {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(f > 0 ? -0.7 : Math.PI + 0.7);
  ctx.fillStyle = '#4a4f57';
  ctx.fillRect(0, -0.35 * S, 3 * S, 0.7 * S);
  ctx.fillStyle = '#6b7178';
  ctx.fillRect(0, -0.35 * S, 0.8 * S, 0.7 * S);
  const pulse = 0.7 + 0.3 * Math.sin(t * 14);
  const g = ctx.createRadialGradient(3 * S, 0, 0, 3 * S, 0, 1.3 * S * pulse);
  g.addColorStop(0, 'rgba(150,255,170,0.95)');
  g.addColorStop(1, 'rgba(70,255,120,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(3 * S, 0, 1.3 * S * pulse, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#e6fff0';
  ctx.beginPath();
  ctx.arc(3 * S, 0, 0.35 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawTardis(ctx: CanvasRenderingContext2D, tx: number, groundY: number, S: number, opacity: number, t: number): void {
  if (opacity <= 0.02) return;
  ctx.save();
  const flick = 0.85 + 0.15 * Math.sin(t * 30);
  ctx.globalAlpha = Math.min(1, opacity) * flick;
  const w = 6 * S;
  const h = 11 * S;
  const x = tx - w / 2;
  const y = groundY - h;
  ctx.fillStyle = '#1b3a6b';
  ctx.fillRect(x, y, w, h);
  ctx.fillStyle = '#16315c';
  ctx.fillRect(x + 0.4 * S, y + 2.2 * S, w - 0.8 * S, h - 2.6 * S);
  ctx.fillStyle = '#dfeeff';
  ctx.fillRect(x + 0.5 * S, y + 0.3 * S, w - 1 * S, 0.9 * S);
  ctx.fillStyle = '#bfe0ff';
  ctx.fillRect(x + 1 * S, y + 2.8 * S, 1.4 * S, 1.4 * S);
  ctx.fillRect(x + w - 2.4 * S, y + 2.8 * S, 1.4 * S, 1.4 * S);
  ctx.fillStyle = '#eaf6ff';
  ctx.fillRect(tx - 0.5 * S, y - 1 * S, 1 * S, 1 * S);
  const g = ctx.createRadialGradient(tx, y - 0.5 * S, 0, tx, y - 0.5 * S, 2 * S);
  g.addColorStop(0, 'rgba(180,230,255,0.7)');
  g.addColorStop(1, 'rgba(120,200,255,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(tx, y - 0.5 * S, 2 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// ── actions ──────────────────────────────────────────────────────────────────
export interface Action {
  name: string;
  dur: number;
  speed: number; // px/sec horizontal movement
  pose: (t: number) => Pose; // t in 0..1
  /** Optional extra drawing (props / portals / tardis) on top of the figure. */
  fx?: (ctx: CanvasRenderingContext2D, x: number, gy: number, S: number, f: 1 | -1, t: number) => void;
}

const TAU = Math.PI * 2;

export const ACTIONS: Record<string, Action> = {
  // ── base set ──
  idle: { name: 'idle', dur: 2.2, speed: 0, pose: (t) => stand({ bob: Math.sin(t * TAU) * 0.5, blink: t > 0.46 && t < 0.52 }) },
  walk: {
    name: 'walk',
    dur: 3,
    speed: 24,
    pose: (t) => {
      const ph = t * TAU * 4;
      return stand({
        step: Math.sin(ph),
        bob: -Math.abs(Math.sin(ph)) * 0.6,
        armL: Math.sin(ph) > 0 ? 'fore' : 'down',
        armR: Math.sin(ph) < 0 ? 'fore' : 'down',
      });
    },
  },
  wave: { name: 'wave', dur: 1.5, speed: 0, pose: (t) => stand({ armR: Math.sin(t * Math.PI * 8) > 0 ? 'up' : 'out', bob: Math.sin(t * TAU) * 0.3 }) },
  jump: { name: 'jump', dur: 0.9, speed: 0, pose: (t) => stand({ bob: -Math.sin(t * Math.PI) * 7, armL: 'up', armR: 'up' }) },
  think: { name: 'think', dur: 2.4, speed: 0, pose: (t) => stand({ armR: 'head', bob: Math.sin(t * TAU) * 0.3 }) },
  laugh: { name: 'laugh', dur: 1.4, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI * 10) * 0.4, bob: -Math.abs(Math.sin(t * Math.PI * 5)) }) },
  trip: { name: 'trip', dur: 1.0, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI) * 1.3, bob: -Math.sin(t * Math.PI) * 2, step: t < 0.5 ? 1 : -1, armL: 'out', armR: 'out' }) },
  point: { name: 'point', dur: 1.5, speed: 0, pose: (t) => stand({ armR: 'fore', bob: Math.sin(t * TAU) * 0.2 }) },
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

  // ── new shared actions ──
  cheer: { name: 'cheer', dur: 1.2, speed: 0, pose: (t) => stand({ armL: 'up', armR: 'up', bob: -Math.abs(Math.sin(t * TAU)) * 3 }) },
  shrug: { name: 'shrug', dur: 1.1, speed: 0, pose: (t) => stand({ armL: 'out', armR: 'out', lean: Math.sin(t * Math.PI) * 0.15 }) },
  stretch: { name: 'stretch', dur: 1.6, speed: 0, pose: (t) => stand({ armL: 'up', armR: 'up', bob: -Math.sin(t * Math.PI) * 1.5 }) },
  lookAround: { name: 'lookAround', dur: 1.8, speed: 0, pose: (t) => stand({ lean: Math.sin(t * TAU) * 0.4 }) },
  facepalm: { name: 'facepalm', dur: 1.6, speed: 0, pose: (t) => stand({ armR: 'head', bob: 0.5, blink: t > 0.3 }) },
  run: {
    name: 'run',
    dur: 1.6,
    speed: 60,
    pose: (t) => {
      const ph = t * TAU * 6;
      return stand({ step: Math.sin(ph), bob: -Math.abs(Math.sin(ph)) * 1, lean: 0.4, armL: Math.sin(ph) > 0 ? 'fore' : 'down', armR: Math.sin(ph) < 0 ? 'fore' : 'down' });
    },
  },

  // ── DOC-R (Rick-style) specials ──
  portalGun: {
    name: 'portalGun',
    dur: 2.0,
    speed: 0,
    pose: (t) => stand({ armR: 'fore', lean: 0.15, bob: Math.sin(t * TAU) * 0.3 }),
    fx: (ctx, x, gy, S, f, t) => {
      drawPortalGun(ctx, x + f * 3.6 * S, gy - 9 * S, S, f);
      if (Math.sin(t * Math.PI * 6) > 0.7) drawPortal(ctx, x + f * 7 * S, gy - 8 * S, 1.6 * S, t);
    },
  },
  portalChaos: {
    name: 'portalChaos',
    dur: 4.0,
    speed: 0,
    pose: (t) => {
      if (t < 0.26) return stand({ armR: 'fore', lean: 0.2 }); // aim
      if (t < 0.85) return stand({ armR: 'up', armL: 'up', lean: -0.6, bob: -1, scared: true }); // recoil, scared
      return stand({ armR: 'fore', lean: 0.1 }); // close
    },
    fx: (ctx, x, gy, S, f, t) => {
      const portalX = x + f * 9 * S;
      const portalY = gy - 7 * S;
      const open = t < 0.85 ? Math.min(1, t / 0.22) : Math.max(0, (1 - t) / 0.15);
      drawPortal(ctx, portalX, portalY, 3.4 * S * open, t);
      const ten = t > 0.3 && t < 0.88 ? Math.min(1, (t - 0.3) / 0.18) * Math.min(1, (0.88 - t) / 0.12) : 0;
      if (ten > 0.05) drawTentacles(ctx, portalX, portalY, 7 * S * ten, t, 4, f);
      drawPortalGun(ctx, x + f * 3.6 * S, gy - 9 * S, S, f);
    },
  },
  drink: {
    name: 'drink',
    dur: 1.8,
    speed: 0,
    pose: (t) => stand({ armR: 'head', lean: t < 0.5 ? -0.15 : 0, bob: Math.sin(t * TAU) * 0.3 }),
    fx: (ctx, x, gy, S, f) => {
      ctx.fillStyle = '#9aa3ad';
      ctx.fillRect(x + f * 1.2 * S - 0.8 * S, gy - 12.5 * S, 1.6 * S, 2.4 * S);
      ctx.fillStyle = '#c8d0d8';
      ctx.fillRect(x + f * 1.2 * S - 0.8 * S, gy - 12.5 * S, 1.6 * S, 0.5 * S);
    },
  },
  burp: {
    name: 'burp',
    dur: 0.9,
    speed: 0,
    pose: (t) => stand({ bob: -Math.abs(Math.sin(t * Math.PI * 3)) * 1, lean: Math.sin(t * Math.PI * 6) * 0.2 }),
    fx: (ctx, x, gy, S, f, t) => {
      ctx.save();
      ctx.globalAlpha = 0.5 * (1 - t);
      ctx.fillStyle = '#9bd86a';
      ctx.beginPath();
      ctx.arc(x + f * 3 * S, gy - 13 * S, (1 + t * 2.5) * S, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    },
  },

  // ── THE TRAVELLER (Doctor-style) specials ──
  sonicScan: {
    name: 'sonicScan',
    dur: 2.2,
    speed: 0,
    pose: (t) => stand({ armR: 'up', bob: Math.sin(t * TAU) * 0.3, lean: Math.sin(t * Math.PI * 4) * 0.12 }),
    fx: (ctx, x, gy, S, f, t) => drawSonic(ctx, x + f * 3.2 * S, gy - 10 * S, S, f, t),
  },
  tardisVisit: {
    name: 'tardisVisit',
    dur: 4.0,
    speed: 0,
    pose: (t) => {
      if (t < 0.3) return stand({ armR: 'fore' });
      if (t < 0.72) return stand({ armR: 'up' });
      return stand({ armR: 'up', lean: 0.1 });
    },
    fx: (ctx, x, gy, S, f, t) => {
      const op = t < 0.3 ? t / 0.3 : t > 0.72 ? Math.max(0, (1 - t) / 0.28) : 1;
      drawTardis(ctx, x + f * 8 * S, gy, S, op, t);
      if (t >= 0.3 && t < 0.74) drawSonic(ctx, x + f * 3.2 * S, gy - 10 * S, S, f, t);
    },
  },
  tipHat: {
    name: 'tipHat',
    dur: 1.4,
    speed: 0,
    pose: (t) => stand({ lean: Math.sin(t * Math.PI) * 0.5, armR: t < 0.5 ? 'head' : 'down', bob: Math.sin(t * Math.PI) * 1 }),
  },
};

// Per-character action weights (DOC-R goofier; THE TRAVELLER calmer). Each only
// gets its own gadgets — Rick never summons a TARDIS, the Traveller no portals.
export const WEIGHTS_DOCR: Record<string, number> = {
  idle: 4, walk: 5, wave: 2, jump: 3, think: 1, laugh: 3, trip: 2, point: 2, gadget: 1, sit: 1, dance: 2, glitch: 1,
  cheer: 2, shrug: 1, stretch: 1, lookAround: 2, facepalm: 1, run: 2,
  portalGun: 3, portalChaos: 2, drink: 2, burp: 2,
};
export const WEIGHTS_TRAVELLER: Record<string, number> = {
  idle: 5, walk: 5, wave: 2, jump: 1, think: 4, laugh: 1, trip: 1, point: 3, gadget: 1, sit: 2, dance: 1, glitch: 1,
  cheer: 1, shrug: 2, stretch: 1, lookAround: 3, facepalm: 1, run: 1,
  sonicScan: 3, tardisVisit: 2, tipHat: 2,
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

// Short, catchphrase-style one-liners (English), in the spirit of each archetype.
export const LINES_DOCR = [
  'Wubba lubba dub dub!',
  'Get schwifty!',
  "And that's the way the news goes!",
  "I'm Pickle Riiick!",
  'Riggity-wrecked, son!',
  'Nobody exists on purpose.',
  "Don't even trip.",
];
export const LINES_TRAVELLER = [
  'Allons-y!',
  'Geronimo!',
  'Fantastic!',
  'Wibbly wobbly, timey wimey.',
  'Bow ties are cool.',
  'Run!',
  'Would you like a jelly baby?',
];

export { GW, GH };
