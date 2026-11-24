// Parametric pixel-art "residents" for the HUD.
//
// COPYRIGHT NOTE: DOC-R and THE TRAVELLER are ORIGINAL parody pixel figures, only
// loosely inspired by two archetypes (a manic inventor / a time-wandering gentleman).
// The Traveller's three "reforms" (X / XI / XII) are fan-style costume homages — generic
// 10×16 pixel figures that only borrow outfit cues (coat cut, neckwear, hair, colours).
// Everything else is our own design drawn from scratch: the time machine is an original
// brass-and-glass CAPSULE, the pursuing robot is an original orb drone, and all
// speech-bubble lines are original quips. Don't add official names, logos, the police
// box, or show catchphrases.

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
  smile?: boolean;
}

export type HairStyle = 'spiky' | 'swept' | 'curly' | 'short' | 'long' | 'quiff' | 'floppy' | 'backswept';
export type Accessory = 'none' | 'goggles' | 'scarf' | 'satchel' | 'cap';
export type Neckwear = 'none' | 'tie' | 'bowtie' | 'buttoned';

export interface CharDef {
  name: string;
  hair: string;
  hair2: string;
  coat: string;
  shirt: string;
  skin: string;
  pants: string;
  hairStyle: HairStyle;
  accessory: Accessory;
  accColor: string;
  glow: string;
  // ── optional costume details (all off by default) ──
  /** Coat skirt hangs down past the knees. */
  longCoat?: boolean;
  /** Jacket / waistcoat worn under the open coat. */
  suit?: string;
  neck?: Neckwear;
  neckColor?: string;
  /** Braces (suspenders) over the shirt. */
  braces?: string;
  /** Coloured lining showing along the open coat front. */
  lining?: string;
  /** Heavy eyebrows in this colour. */
  brows?: string;
  shoes?: string;
  shoeSole?: string;
  /** Glow colour of the hand-held scanner's tip (#rrggbb). */
  wandGlow?: string;
}

export const DOCR: CharDef = {
  name: 'DOC-R',
  hair: '#9fe0f2',
  hair2: '#5fb8d8',
  coat: '#eef1f4',
  shirt: '#3a6ea5',
  skin: '#e7b48a',
  pants: '#2b3b46',
  hairStyle: 'spiky',
  accessory: 'none',
  accColor: '#000',
  glow: 'rgba(120,255,150,0.45)',
};

/** Form X — tall spiky quiff, long brown coat over a brown suit, blue shirt + tie,
 *  cream canvas high-tops, blue-tipped scanner. */
export const TRAVELLER: CharDef = {
  name: 'TRAVELLER·X',
  hair: '#3a2417',
  hair2: '#5c3a22',
  coat: '#8d6a45',
  shirt: '#b7cbe3',
  skin: '#efc3a0',
  pants: '#4e3a2e',
  hairStyle: 'quiff',
  accessory: 'none',
  accColor: '#000',
  glow: 'rgba(120,190,255,0.45)',
  longCoat: true,
  suit: '#56402f',
  neck: 'tie',
  neckColor: '#7c2b2b',
  shoes: '#ece5d3',
  shoeSole: '#ffffff',
  wandGlow: '#5aa8ff',
};

/** The Traveller's three looks — he "reforms" into another one now and then. */
export const TRAVELLER_FORMS: CharDef[] = [
  TRAVELLER,
  /** Form XI — floppy side fringe, short tweed jacket, red bow tie + braces,
   *  short dark trousers, black boots, green-tipped scanner. */
  {
    ...TRAVELLER,
    name: 'TRAVELLER·XI',
    hair: '#5a3920',
    hair2: '#3d2614',
    coat: '#7a5638',
    shirt: '#e2ddd2',
    skin: '#f1caa8',
    pants: '#26262c',
    hairStyle: 'floppy',
    glow: 'rgba(140,255,150,0.45)',
    longCoat: false,
    suit: undefined,
    neck: 'bowtie',
    neckColor: '#b3202b',
    braces: '#9e2430',
    shoes: '#17171a',
    shoeSole: '#2c2c30',
    wandGlow: '#62f07a',
  },
  /** Form XII — swept-back silver hair, stern brows, long dark navy coat with red
   *  lining, dark waistcoat, white shirt buttoned to the top, black boots. */
  {
    ...TRAVELLER,
    name: 'TRAVELLER·XII',
    hair: '#cfd3d6',
    hair2: '#9fa5aa',
    coat: '#242b3f',
    shirt: '#eef0f2',
    skin: '#e6b891',
    pants: '#1a1d25',
    hairStyle: 'backswept',
    glow: 'rgba(255,120,120,0.40)',
    longCoat: true,
    suit: '#2b3040',
    neck: 'buttoned',
    neckColor: '#59606a',
    lining: '#a5202d',
    brows: '#4b4e53',
    shoes: '#121214',
    shoeSole: '#2a2a2e',
    wandGlow: '#62f07a',
  },
];

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

/** Darken (k < 1) or lighten (k > 1) a #rrggbb colour. */
function shade(hex: string, k: number): string {
  const n = parseInt(hex.slice(1), 16);
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v * k)));
  return `rgb(${c((n >> 16) & 255)},${c((n >> 8) & 255)},${c(n & 255)})`;
}

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
  const coatDark = shade(def.coat, 0.78);
  const skinDark = shade(def.skin, 0.85);

  const px = (gx: number, gy: number, w: number, h: number, color: string | null) => {
    if (!color) return;
    const mgx = facing < 0 ? GW - gx - w : gx;
    const shift = Math.round(lean * (1 - gy / GH) * 2) * facing;
    ctx.fillStyle = color;
    ctx.fillRect(ox + mgx * S + shift * S, oy + gy * S, w * S, h * S);
  };

  const arm = (pos: ArmPos, side: 'L' | 'R') => {
    const x = side === 'L' ? 2 : 7;
    const sleeve = side === 'L' ? def.coat : coatDark;
    switch (pos) {
      case 'up':
        px(x, 2, 1, 4, sleeve);
        px(x, 1, 1, 1, def.skin);
        break;
      case 'out':
        px(side === 'L' ? 0 : 8, 6, 2, 1, sleeve);
        px(side === 'L' ? -1 : 10, 6, 1, 1, def.skin);
        break;
      case 'head':
        px(x, 4, 1, 2, sleeve);
        px(side === 'L' ? 3 : 6, 3, 1, 1, def.skin);
        break;
      case 'fore':
        px(side === 'L' ? 1 : 8, 7, 2, 1, sleeve);
        px(side === 'L' ? 0 : 9, 7, 1, 1, def.skin);
        if (pose.prop && side === 'R') px(10, 6, 1, 2, '#9be7ff');
        break;
      case 'down':
      default:
        px(x, 6, 1, 5, sleeve);
        px(x, 11, 1, 1, def.skin);
    }
  };

  // legs + shoes
  const shoe = def.shoes ?? '#16191d';
  if (pose.sit) {
    px(3, 12, 2, 2, def.pants);
    px(5, 12, 2, 2, shade(def.pants, 0.8));
    px(2, 13, 1, 1, shoe);
    px(7, 13, 1, 1, shoe);
  } else {
    const sw = pose.step;
    const lx = 3 + (sw < -0.3 ? -1 : 0);
    const rx = 5 + (sw > 0.3 ? 1 : 0);
    px(3, 12, 2, 4, def.pants);
    px(5, 12, 2, 4, shade(def.pants, 0.8));
    px(lx, 15, 2, 1, shoe);
    px(rx, 15, 2, 1, shoe);
    if (def.shoeSole) {
      px(lx, 15.7, 2, 0.3, def.shoeSole);
      px(rx, 15.7, 2, 0.3, def.shoeSole);
    } else {
      px(lx, 15, 1, 0.4, '#3a4048'); // shoe shine
    }
  }

  // body: coat with a shaded side, open front (shirt) and lapels
  px(3, 6, 4, 6, def.coat);
  px(6, 6, 1, 6, coatDark);
  if (def.suit) {
    // jacket / waistcoat under the open coat, shirt showing as a V at the top
    px(3.7, 6, 2.6, 5.2, def.suit);
    px(5.6, 6, 0.7, 5.2, shade(def.suit, 0.8));
    px(4.45, 6, 1.1, 2.6, def.shirt);
    px(4.7, 8.6, 0.6, 0.4, def.shirt);
  } else {
    px(4, 6, 2, 5, def.shirt);
  }
  if (def.braces) {
    px(4.05, 6, 0.35, 5, def.braces);
    px(5.6, 6, 0.35, 5, def.braces);
  }
  if (def.lining) {
    const lh = def.longCoat ? (pose.sit ? 7.2 : 7.9) : 5;
    px(3.65, 6, 0.35, lh, def.lining);
    px(6.0, 6, 0.35, lh, shade(def.lining, 0.8));
  }
  if (def.suit || (def.neck && def.neck !== 'none')) {
    // slim lapels so the collar / neckwear stays visible
    px(4, 6, 0.45, 1.2, coatDark);
    px(5.55, 6, 0.45, 1.2, coatDark);
  } else {
    px(4, 6, 1, 1, coatDark); // lapel
    px(5, 6, 1, 1, coatDark);
  }
  if (def.neck === 'tie' && def.neckColor) {
    px(4.7, 6, 0.6, 0.6, shade(def.neckColor, 0.8)); // knot
    px(4.78, 6.6, 0.44, 2.6, def.neckColor);
    px(4.7, 9.1, 0.6, 0.4, def.neckColor);
  } else if (def.neck === 'bowtie' && def.neckColor) {
    px(3.95, 5.85, 0.85, 0.75, def.neckColor);
    px(5.2, 5.85, 0.85, 0.75, def.neckColor);
    px(4.7, 5.95, 0.6, 0.55, shade(def.neckColor, 0.72)); // knot
  } else if (def.neck === 'buttoned') {
    px(4.4, 5.9, 1.2, 0.35, shade(def.shirt, 0.88)); // closed collar
    px(4.85, 6.35, 0.3, 0.3, def.neckColor ?? '#59606a'); // top button
  }

  if (def.longCoat) {
    // open coat skirt hanging past the knees on both sides of the legs
    const bottom = pose.sit ? 13.6 : 14.3;
    px(2.6, 11, 1.5, bottom - 11, def.coat);
    px(5.9, 11, 1.5, bottom - 11, coatDark);
    px(2.6, bottom - 0.4, 1.5, 0.4, shade(def.coat, 0.65)); // hems
    px(5.9, bottom - 0.4, 1.5, 0.4, shade(def.coat, 0.55));
    px(3, 6, 0.3, 5, shade(def.coat, 1.12)); // collar light edge
  } else {
    px(3, 11, 4, 0.5, shade(def.coat, 0.65)); // hem
  }

  // accessories under the arms
  if (def.accessory === 'satchel') {
    px(3, 6, 1, 1, def.accColor);
    px(4, 7, 1, 1, def.accColor);
    px(5, 8, 1, 1, def.accColor);
    px(6, 9, 2, 2, def.accColor);
  }

  arm(pose.armL, 'L');
  arm(pose.armR, 'R');

  // head + face
  px(3, 2, 4, 4, def.skin);
  px(6, 2, 1, 4, skinDark);
  if (pose.scared) {
    px(4, 3.6, 1, 1.2, '#21262c');
    px(6, 3.6, 1, 1.2, '#21262c');
    px(3, 3, 1, 0.5, '#21262c');
    px(7, 3, 1, 0.5, '#21262c');
    px(4.5, 5, 1.2, 0.9, '#1a1414');
  } else {
    if (!pose.blink) {
      px(4, 4, 1, 1, '#21262c');
      px(6, 4, 1, 1, '#21262c');
      px(4.55, 4, 0.4, 0.4, '#e8f6ff'); // eye shine
    } else {
      px(4, 4.4, 3, 0.4, '#21262c');
    }
    px(4, 5.2, 2, 0.4, pose.smile ? '#b5523f' : '#8a5040'); // mouth
    if (pose.smile) px(3.6, 5, 0.4, 0.4, '#b5523f');
  }
  if (def.brows) {
    // heavy, slanted brows (inner ends lower = stern look; raised when scared)
    const up = pose.scared ? -0.5 : 0;
    px(3.8, 3.25 + up, 0.7, 0.4, def.brows);
    px(4.5, 3.45 + up, 0.7, 0.4, def.brows);
    px(5.8, 3.45 + up, 0.7, 0.4, def.brows);
    px(6.5, 3.25 + up, 0.7, 0.4, def.brows);
  }

  // hair
  const H = def.hair;
  const H2 = def.hair2;
  switch (def.hairStyle) {
    case 'spiky':
      px(3, 1, 4, 1, H);
      px(2, 1, 1, 1, H);
      px(7, 1, 1, 1, H);
      px(3, 0, 1, 1, H);
      px(5, 0, 1, 1, H);
      px(6, 0, 1, 1, H);
      px(2, 0, 0.6, 0.6, H2);
      px(7.4, 0, 0.6, 0.6, H2);
      px(4, 1, 1, 1, H2);
      break;
    case 'curly':
      px(2, 1, 6, 2, H);
      px(2, 0.4, 1, 1, H2);
      px(3.5, 0, 1, 1, H);
      px(5, 0.2, 1, 1, H2);
      px(6.5, 0, 1, 1, H);
      px(2, 3, 1, 1, H2);
      px(7, 3, 1, 1, H2);
      break;
    case 'short':
      px(3, 1, 4, 1, H);
      px(3, 0.5, 4, 0.5, H2);
      px(2.6, 1.5, 0.4, 1, H2);
      break;
    case 'long':
      px(2, 1, 6, 1, H);
      px(3, 0, 4, 1, H2);
      px(2, 2, 1, 4, H);
      px(7, 2, 1, 4, H);
      px(2, 6, 1, 1, H2);
      px(7, 6, 1, 1, H2);
      break;
    case 'quiff':
      // tall, spiky, brushed-up front + sideburns; forehead stays clear
      px(3, 1, 4, 1.2, H);
      px(2.6, 1.4, 0.6, 1.6, H);
      px(6.8, 1.4, 0.6, 1.6, H);
      px(3, 3, 0.4, 1.4, H2); // sideburns
      px(6.6, 3, 0.4, 1.4, H2);
      px(3.3, 0.2, 1.1, 1, H);
      px(4.3, -0.7, 1.3, 1.8, H);
      px(5.5, -0.4, 1.1, 1.5, H);
      px(6.4, 0.3, 0.8, 0.9, H);
      px(4.6, -0.5, 0.5, 0.6, H2); // highlights
      px(5.8, -0.2, 0.4, 0.5, H2);
      break;
    case 'floppy':
      // voluminous top with a fringe swept across the forehead to one side
      px(2.4, 0.6, 5.2, 1.6, H);
      px(3, 0, 3.8, 0.8, H);
      px(2.4, 2.2, 0.8, 1.7, H);
      px(6.8, 2.2, 0.8, 1.3, H);
      px(3, 2, 3.8, 0.5, H);
      px(4.4, 2.5, 2.4, 0.5, H);
      px(5.6, 3.0, 1.3, 0.45, H2);
      px(3.5, 0.25, 1.5, 0.4, H2); // highlight
      break;
    case 'backswept':
      // swept-back silver waves, high crown, clear forehead, grey temples
      px(2.6, 0.8, 4.8, 1.3, H);
      px(3.3, 0.1, 3.8, 0.9, H);
      px(5.4, -0.4, 2, 1, H);
      px(2.4, 1.9, 0.7, 1.7, H2);
      px(6.9, 1.9, 0.7, 1.7, H2);
      px(3.3, 0.5, 0.7, 0.35, H2); // waves
      px(4.6, 0.25, 0.7, 0.35, H2);
      px(5.9, -0.1, 0.7, 0.35, H2);
      break;
    case 'swept':
    default:
      px(2, 1, 6, 2, H);
      px(2, 3, 1, 1, H2);
      px(7, 3, 1, 1, H2);
      px(3, 0, 4, 1, H2);
      px(6, 0.4, 2, 0.6, H);
  }

  // head accessories
  if (def.accessory === 'goggles') {
    px(2, 1.6, 6, 0.5, '#3a3226');
    px(3, 1.2, 1.4, 1.2, def.accColor);
    px(5.6, 1.2, 1.4, 1.2, def.accColor);
    px(3.3, 1.5, 0.6, 0.5, '#bff3ff');
    px(5.9, 1.5, 0.6, 0.5, '#bff3ff');
  } else if (def.accessory === 'cap') {
    px(2, 0, 6, 1.2, def.accColor);
    px(6, 1, 3, 0.5, shade(def.accColor, 0.7)); // brim
  } else if (def.accessory === 'scarf') {
    px(3, 5.6, 4, 0.9, def.accColor);
    px(3, 6.5, 1, 2.2, def.accColor);
    px(3, 8.4, 1, 0.4, shade(def.accColor, 0.7));
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

export function drawPortal(ctx: CanvasRenderingContext2D, px: number, py: number, R: number, t: number): void {
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

function drawTentacles(ctx: CanvasRenderingContext2D, px: number, py: number, len: number, t: number, count: number, f: 1 | -1): void {
  ctx.save();
  ctx.strokeStyle = '#5fdc4a';
  ctx.lineWidth = Math.max(1.5, len * 0.06);
  ctx.lineCap = 'round';
  const baseAng = f > 0 ? Math.PI : 0;
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

/** #rrggbb → rgba() with the given alpha. */
function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function drawWand(ctx: CanvasRenderingContext2D, hx: number, hy: number, S: number, f: 1 | -1, t: number, glow = '#ffb84a'): void {
  ctx.save();
  ctx.translate(hx, hy);
  ctx.rotate(f > 0 ? -0.7 : Math.PI + 0.7);
  ctx.fillStyle = '#4a4f57';
  ctx.fillRect(0, -0.35 * S, 3 * S, 0.7 * S);
  ctx.fillStyle = '#b88a3a';
  ctx.fillRect(0, -0.35 * S, 0.8 * S, 0.7 * S);
  const pulse = 0.7 + 0.3 * Math.sin(t * 14);
  const g = ctx.createRadialGradient(3 * S, 0, 0, 3 * S, 0, 1.3 * S * pulse);
  g.addColorStop(0, rgba(glow, 0.95));
  g.addColorStop(1, rgba(glow, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(3 * S, 0, 1.3 * S * pulse, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#f4fbff';
  ctx.beginPath();
  ctx.arc(3 * S, 0, 0.35 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/** The Traveller's ORIGINAL time machine: an upright brass-and-glass capsule with a
 *  spinning ring and a swirling teal core. `op` 0..1 (it shimmers in and out). */
export function drawTimePod(ctx: CanvasRenderingContext2D, cx: number, groundY: number, S: number, op: number, t: number): void {
  if (op <= 0.02) return;
  ctx.save();
  const flick = 0.82 + 0.18 * Math.sin(t * 40);
  ctx.globalAlpha = Math.min(1, op) * (op < 1 ? flick : 1);
  const w = 7 * S;
  const h = 13 * S;
  const x = cx - w / 2;
  const top = groundY - h;
  // base plate
  ctx.fillStyle = '#6b5326';
  ctx.fillRect(x - 0.6 * S, groundY - 1 * S, w + 1.2 * S, 1 * S);
  // glass body (rounded capsule)
  const body = ctx.createLinearGradient(x, 0, x + w, 0);
  body.addColorStop(0, 'rgba(60,140,150,0.55)');
  body.addColorStop(0.5, 'rgba(140,240,240,0.35)');
  body.addColorStop(1, 'rgba(40,110,120,0.6)');
  ctx.fillStyle = body;
  ctx.beginPath();
  ctx.ellipse(cx, top + 3 * S, w / 2, 3 * S, 0, Math.PI, 0);
  ctx.lineTo(x + w, groundY - 1 * S);
  ctx.lineTo(x, groundY - 1 * S);
  ctx.closePath();
  ctx.fill();
  // swirling core
  ctx.strokeStyle = 'rgba(180,255,250,0.75)';
  ctx.lineWidth = Math.max(1, 0.35 * S);
  for (let i = 0; i < 3; i++) {
    const a = t * 8 + i * 2.1;
    ctx.beginPath();
    ctx.ellipse(cx, top + 7 * S, (1.2 + i * 0.7) * S, (2.2 + i * 0.9) * S, 0, a, a + 1.6);
    ctx.stroke();
  }
  // brass frame + spinning ring
  ctx.strokeStyle = '#c99a42';
  ctx.lineWidth = Math.max(1, 0.5 * S);
  ctx.beginPath();
  ctx.moveTo(x, groundY - 1 * S);
  ctx.lineTo(x, top + 3 * S);
  ctx.moveTo(x + w, groundY - 1 * S);
  ctx.lineTo(x + w, top + 3 * S);
  ctx.stroke();
  const ringW = (w / 2 + 1.2 * S) * Math.abs(Math.cos(t * 5));
  ctx.strokeStyle = '#e8c070';
  ctx.beginPath();
  ctx.ellipse(cx, top + 7.5 * S, Math.max(1, ringW), 0.9 * S, 0, 0, Math.PI * 2);
  ctx.stroke();
  // beacon
  const g = ctx.createRadialGradient(cx, top - 0.4 * S, 0, cx, top - 0.4 * S, 2.4 * S);
  g.addColorStop(0, 'rgba(255,230,150,0.9)');
  g.addColorStop(1, 'rgba(255,200,90,0)');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, top - 0.4 * S, 2.4 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/** Swirling sparkles while the Traveller reforms into a new look. */
function drawReform(ctx: CanvasRenderingContext2D, cx: number, groundY: number, S: number, t: number): void {
  ctx.save();
  const k = Math.sin(t * Math.PI);
  for (let i = 0; i < 14; i++) {
    const a = t * 14 + i * 0.9;
    const r = (3 + (i % 4)) * S * (0.6 + k * 0.6);
    const x = cx + Math.cos(a) * r;
    const y = groundY - 8 * S + Math.sin(a * 1.3) * r * 0.9;
    ctx.globalAlpha = 0.25 + 0.6 * k;
    ctx.fillStyle = i % 2 ? '#8fe9ff' : '#d9b8ff';
    ctx.fillRect(x - 0.4 * S, y - 0.4 * S, 0.8 * S, 0.8 * S);
  }
  const g = ctx.createRadialGradient(cx, groundY - 8 * S, 0, cx, groundY - 8 * S, 9 * S);
  g.addColorStop(0, `rgba(200,240,255,${0.45 * k})`);
  g.addColorStop(1, 'rgba(160,120,255,0)');
  ctx.globalAlpha = 1;
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, groundY - 8 * S, 9 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawFlask(ctx: CanvasRenderingContext2D, hx: number, hy: number, S: number, t: number): void {
  ctx.save();
  ctx.fillStyle = 'rgba(200,230,240,0.55)';
  ctx.fillRect(hx - 0.5 * S, hy - 2.6 * S, 1 * S, 1.2 * S);
  ctx.beginPath();
  ctx.moveTo(hx - 0.5 * S, hy - 1.4 * S);
  ctx.lineTo(hx - 1.5 * S, hy + 0.6 * S);
  ctx.lineTo(hx + 1.5 * S, hy + 0.6 * S);
  ctx.lineTo(hx + 0.5 * S, hy - 1.4 * S);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = `hsl(${(t * 900) % 360},90%,60%)`;
  ctx.fillRect(hx - 1.1 * S, hy - 0.2 * S, 2.2 * S, 0.8 * S);
  for (let i = 0; i < 3; i++) {
    const by = hy - 1.5 * S - ((t * 6 + i * 0.33) % 1) * 3 * S;
    ctx.fillStyle = 'rgba(200,255,220,0.7)';
    ctx.beginPath();
    ctx.arc(hx + (i - 1) * 0.5 * S, by, 0.35 * S, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

export function drawSmoke(ctx: CanvasRenderingContext2D, cx: number, cy: number, S: number, k: number): void {
  ctx.save();
  for (let i = 0; i < 7; i++) {
    const a = i * 0.9;
    const r = (1.5 + k * 4) * S;
    ctx.globalAlpha = 0.55 * (1 - k);
    ctx.fillStyle = i % 2 ? '#8c939b' : '#b7bec5';
    ctx.beginPath();
    ctx.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r * 0.7 - k * 3 * S, (1.6 + k * 2) * S, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawJetFlame(ctx: CanvasRenderingContext2D, cx: number, y: number, S: number, t: number): void {
  ctx.save();
  ctx.fillStyle = '#5a636d';
  ctx.fillRect(cx - 2 * S, y - 9 * S, 1.4 * S, 3 * S);
  ctx.fillRect(cx + 0.6 * S, y - 9 * S, 1.4 * S, 3 * S);
  for (const dx of [-1.3, 1.3]) {
    const len = (2.5 + Math.sin(t * 60 + dx) * 0.8) * S;
    const g = ctx.createLinearGradient(0, y - 6 * S, 0, y - 6 * S + len);
    g.addColorStop(0, 'rgba(255,240,170,0.95)');
    g.addColorStop(1, 'rgba(255,110,40,0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(cx + dx * S - 0.7 * S, y - 6 * S);
    ctx.lineTo(cx + dx * S + 0.7 * S, y - 6 * S);
    ctx.lineTo(cx + dx * S, y - 6 * S + len);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

// ── visitors (things that show up, follow, and vanish) — all original designs ──
export type VisitorKind = 'dino' | 'drone' | 'saucer' | 'duck' | 'blob';

/** Draw a visitor at (x, groundY), facing f, animation time t (s), alpha a. */
export function drawVisitor(
  ctx: CanvasRenderingContext2D,
  kind: VisitorKind,
  x: number,
  groundY: number,
  S: number,
  f: 1 | -1,
  t: number,
  a: number,
): void {
  if (a <= 0.02) return;
  ctx.save();
  ctx.globalAlpha = Math.min(1, a);
  const p = (gx: number, gy: number, w: number, h: number, c: string, W: number, ox: number, oy: number) => {
    const mx = f < 0 ? W - gx - w : gx;
    ctx.fillStyle = c;
    ctx.fillRect(ox + mx * S, oy + gy * S, w * S, h * S);
  };
  if (kind === 'dino') {
    // a stompy little original pixel dinosaur (16×12), side view
    const W = 16;
    const H = 12;
    const ox = x - (W / 2) * S;
    const oy = groundY - H * S - Math.abs(Math.sin(t * 9)) * 0.8 * S;
    const G = '#4fae5a';
    const D = '#357a3e';
    const B = '#a7dc8c';
    p(0, 5, 4, 2, D, W, ox, oy); // tail
    p(3, 4, 8, 5, G, W, ox, oy); // body
    p(4, 7, 6, 2, B, W, ox, oy); // belly
    p(10, 1, 5, 4, G, W, ox, oy); // head
    p(11, 0, 3, 1, D, W, ox, oy); // brow ridge
    p(13, 2, 1, 1, '#1b1b1b', W, ox, oy); // eye
    p(14, 4, 2, 1, '#f4f1e8', W, ox, oy); // teeth
    p(11, 6, 1, 2, D, W, ox, oy); // tiny arm
    const step = Math.sin(t * 9) > 0;
    p(5, 9, 2, step ? 3 : 2, D, W, ox, oy);
    p(8, 9, 2, step ? 2 : 3, D, W, ox, oy);
    p(4, 3, 1, 1, D, W, ox, oy); // back spikes
    p(6, 3, 1, 1, D, W, ox, oy);
    p(8, 3, 1, 1, D, W, ox, oy);
  } else if (kind === 'drone') {
    // ORIGINAL hovering orb drone: round shell, one cyan eye, antenna, hover glow
    const cy = groundY - 9 * S + Math.sin(t * 4) * 1.2 * S;
    const g = ctx.createRadialGradient(x, groundY - 1 * S, 0, x, groundY - 1 * S, 5 * S);
    g.addColorStop(0, 'rgba(120,220,255,0.35)');
    g.addColorStop(1, 'rgba(120,220,255,0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(x, groundY - 1 * S, 5 * S, 1.6 * S, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#8a96a3';
    ctx.beginPath();
    ctx.arc(x, cy, 3.4 * S, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#5f6a76';
    ctx.fillRect(x - 3.4 * S, cy, 6.8 * S, 0.6 * S); // seam
    ctx.fillStyle = '#1c2530';
    ctx.beginPath();
    ctx.arc(x + f * 1.2 * S, cy - 0.6 * S, 1.3 * S, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = `rgba(90,240,255,${0.7 + 0.3 * Math.sin(t * 10)})`;
    ctx.beginPath();
    ctx.arc(x + f * 1.2 * S, cy - 0.6 * S, 0.7 * S, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#5f6a76';
    ctx.lineWidth = Math.max(1, 0.3 * S);
    ctx.beginPath();
    ctx.moveTo(x, cy - 3.4 * S);
    ctx.lineTo(x - f * 1 * S, cy - 5.4 * S);
    ctx.stroke();
    ctx.fillStyle = Math.sin(t * 6) > 0 ? '#ff6b6b' : '#7a2b2b';
    ctx.fillRect(x - f * 1 * S - 0.4 * S, cy - 5.8 * S, 0.8 * S, 0.8 * S);
  } else if (kind === 'saucer') {
    const cy = groundY - 26 * S + Math.sin(t * 3) * 2 * S;
    ctx.fillStyle = 'rgba(160,255,200,0.18)';
    if (Math.sin(t * 2) > 0.2) {
      ctx.beginPath();
      ctx.moveTo(x - 1.5 * S, cy + 1.5 * S);
      ctx.lineTo(x + 1.5 * S, cy + 1.5 * S);
      ctx.lineTo(x + 5 * S, groundY);
      ctx.lineTo(x - 5 * S, groundY);
      ctx.closePath();
      ctx.fill();
    }
    ctx.fillStyle = '#9fb0bf';
    ctx.beginPath();
    ctx.ellipse(x, cy, 6 * S, 1.7 * S, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(170,240,255,0.8)';
    ctx.beginPath();
    ctx.ellipse(x, cy - 1.2 * S, 2.6 * S, 1.8 * S, 0, Math.PI, 0);
    ctx.fill();
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = (Math.floor(t * 6) + i) % 2 ? '#ffe17a' : '#ff8ad8';
      ctx.fillRect(x + (i - 1.5) * 2.6 * S - 0.4 * S, cy + 0.2 * S, 0.8 * S, 0.8 * S);
    }
  } else if (kind === 'duck') {
    const W = 8;
    const H = 7;
    const ox = x - (W / 2) * S;
    const oy = groundY - H * S - Math.abs(Math.sin(t * 10)) * 0.5 * S;
    p(1, 3, 6, 3, '#ffd23f', W, ox, oy);
    p(4, 0, 3, 3, '#ffd23f', W, ox, oy);
    p(7, 1, 1, 1, '#ff8c2a', W, ox, oy);
    p(5, 1, 1, 1, '#1b1b1b', W, ox, oy);
    p(0, 3, 1, 1, '#f2b92a', W, ox, oy);
    p(2, 6, 1, 1, '#ff8c2a', W, ox, oy);
    p(5, 6, 1, 1, '#ff8c2a', W, ox, oy);
  } else {
    // blob: a bouncy green slime with eyes (came through a portal)
    const sq = 1 + 0.25 * Math.sin(t * 12);
    const cy = groundY - 2.2 * S * sq - Math.max(0, Math.sin(t * 6)) * 3 * S;
    ctx.fillStyle = 'rgba(110,230,110,0.85)';
    ctx.beginPath();
    ctx.ellipse(x, cy, 3 * S / sq, 2.4 * S * sq, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#e9ffe9';
    ctx.fillRect(x + f * 0.4 * S - 1.4 * S, cy - 1 * S, 1 * S, 1 * S);
    ctx.fillRect(x + f * 0.4 * S + 0.4 * S, cy - 1 * S, 1 * S, 1 * S);
    ctx.fillStyle = '#1b2a1b';
    ctx.fillRect(x + f * 0.8 * S - 1.4 * S, cy - 0.7 * S, 0.5 * S, 0.5 * S);
    ctx.fillRect(x + f * 0.8 * S + 0.4 * S, cy - 0.7 * S, 0.5 * S, 0.5 * S);
  }
  ctx.restore();
}

// ── scene FX helpers (used by the component's joint scenes) ──────────────────
export function drawSpark(ctx: CanvasRenderingContext2D, x: number, y: number, S: number, k: number): void {
  if (k <= 0) return;
  ctx.save();
  ctx.globalAlpha = k;
  ctx.strokeStyle = '#ffe48a';
  ctx.lineWidth = Math.max(1, 0.4 * S);
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(a) * 1.2 * S, y + Math.sin(a) * 1.2 * S);
    ctx.lineTo(x + Math.cos(a) * (2.5 + (1 - k) * 3) * S, y + Math.sin(a) * (2.5 + (1 - k) * 3) * S);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawNotes(ctx: CanvasRenderingContext2D, x: number, groundY: number, S: number, t: number): void {
  ctx.save();
  ctx.font = `${Math.round(4 * S)}px sans-serif`;
  ctx.textAlign = 'center';
  for (let i = 0; i < 3; i++) {
    const k = (t * 0.8 + i / 3) % 1;
    ctx.globalAlpha = 1 - k;
    ctx.fillStyle = i % 2 ? '#8fe9ff' : '#ffd166';
    ctx.fillText(i % 2 ? '♪' : '♫', x + Math.sin(k * 6 + i) * 3 * S, groundY - 18 * S - k * 10 * S);
  }
  ctx.restore();
}

export function drawShootingStar(ctx: CanvasRenderingContext2D, width: number, groundY: number, S: number, k: number): void {
  if (k <= 0 || k >= 1) return;
  const x = width * (0.1 + 0.8 * k);
  const y = Math.max(8, groundY - 38 * S) + k * 10 * S;
  ctx.save();
  const g = ctx.createLinearGradient(x - 18 * S, y - 4 * S, x, y);
  g.addColorStop(0, 'rgba(255,255,255,0)');
  g.addColorStop(1, 'rgba(255,250,220,0.95)');
  ctx.strokeStyle = g;
  ctx.lineWidth = Math.max(1, 0.6 * S);
  ctx.beginPath();
  ctx.moveTo(x - 18 * S, y - 4 * S);
  ctx.lineTo(x, y);
  ctx.stroke();
  ctx.fillStyle = '#fffbe6';
  ctx.beginPath();
  ctx.arc(x, y, 0.9 * S, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// ── actions ──────────────────────────────────────────────────────────────────
/** What an action may do to its actor / the world at a moment of its timeline. */
export interface ActorLike {
  def: CharDef;
  x: number;
  facing: 1 | -1;
  formIdx: number;
  forms?: CharDef[];
}
export interface WorldLike {
  width: number;
  randomX(avoid?: number): number;
  spawn(kind: VisitorKind, x: number, dir: 1 | -1, opts?: { follow?: ActorLike; life?: number; say?: string }): void;
  say(a: ActorLike, text: string, secs?: number): void;
}

export interface Action {
  name: string;
  dur: number;
  speed: number; // px/sec horizontal movement
  pose: (t: number) => Pose; // t in 0..1
  /** Optional extra drawing (props / portals / pod) on top of the figure. */
  fx?: (ctx: CanvasRenderingContext2D, x: number, gy: number, S: number, f: 1 | -1, t: number, def?: CharDef) => void;
  /** Figure opacity over the timeline (vanishing into a pod / portal). Default 1. */
  alpha?: (t: number) => number;
  /** One-shot events at progress `at` (teleport, reform, spawn a visitor, speak…). */
  events?: { at: number; run: (a: ActorLike, w: WorldLike) => void }[];
}

const TAU = Math.PI * 2;
const ramp = (t: number, a: number, b: number) => Math.max(0, Math.min(1, (t - a) / (b - a)));

/** Swap the actor into another of its forms (never the same one twice in a row). */
function nextForm(a: ActorLike): void {
  if (!a.forms || a.forms.length < 2) return;
  let i = a.formIdx;
  while (i === a.formIdx) i = Math.floor(Math.random() * a.forms.length);
  a.formIdx = i;
  a.def = a.forms[i];
}

const VISITORS_AFTER_POD: VisitorKind[] = ['dino', 'drone', 'saucer', 'duck'];
const pick = <T,>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];

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
  wave: { name: 'wave', dur: 1.5, speed: 0, pose: (t) => stand({ armR: Math.sin(t * Math.PI * 8) > 0 ? 'up' : 'out', bob: Math.sin(t * TAU) * 0.3, smile: true }) },
  jump: { name: 'jump', dur: 0.9, speed: 0, pose: (t) => stand({ bob: -Math.sin(t * Math.PI) * 7, armL: 'up', armR: 'up', smile: true }) },
  think: { name: 'think', dur: 2.4, speed: 0, pose: (t) => stand({ armR: 'head', bob: Math.sin(t * TAU) * 0.3 }) },
  laugh: { name: 'laugh', dur: 1.4, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI * 10) * 0.4, bob: -Math.abs(Math.sin(t * Math.PI * 5)), smile: true }) },
  trip: { name: 'trip', dur: 1.0, speed: 0, pose: (t) => stand({ lean: Math.sin(t * Math.PI) * 1.3, bob: -Math.sin(t * Math.PI) * 2, step: t < 0.5 ? 1 : -1, armL: 'out', armR: 'out', scared: t > 0.2 && t < 0.7 }) },
  point: { name: 'point', dur: 1.5, speed: 0, pose: (t) => stand({ armR: 'fore', bob: Math.sin(t * TAU) * 0.2 }) },
  gadget: { name: 'gadget', dur: 1.8, speed: 0, pose: (t) => stand({ armR: 'fore', prop: true, blink: Math.sin(t * Math.PI * 12) > 0 }) },
  sit: { name: 'sit', dur: 2.8, speed: 0, pose: () => stand({ bob: 4, sit: true }) },
  dance: {
    name: 'dance',
    dur: 1.8,
    speed: 0,
    pose: (t) => {
      const ph = t * Math.PI * 8;
      return stand({ lean: Math.sin(ph) * 0.6, bob: -Math.abs(Math.sin(ph)) * 1.5, armL: Math.sin(ph) > 0 ? 'up' : 'out', armR: Math.sin(ph) < 0 ? 'up' : 'out', smile: true });
    },
  },
  glitch: { name: 'glitch', dur: 0.7, speed: 0, pose: (t) => stand({ lean: (Math.random() - 0.5) * 2, bob: (Math.random() - 0.5) * 4, blink: t > 0.3 }) },
  cheer: { name: 'cheer', dur: 1.2, speed: 0, pose: (t) => stand({ armL: 'up', armR: 'up', bob: -Math.abs(Math.sin(t * TAU)) * 3, smile: true }) },
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
  flee: {
    name: 'flee',
    dur: 1.6,
    speed: 0, // moved by the scene
    pose: (t) => {
      const ph = t * TAU * 7;
      return stand({ step: Math.sin(ph), bob: -Math.abs(Math.sin(ph)) * 1.4, lean: 0.55, armL: 'up', armR: 'up', scared: true });
    },
  },
  highFive: { name: 'highFive', dur: 0.9, speed: 0, pose: (t) => stand({ armR: 'up', lean: t < 0.5 ? 0.3 : 0, smile: true }) },

  // ── DOC-R specials ──
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
      if (t < 0.26) return stand({ armR: 'fore', lean: 0.2 });
      if (t < 0.85) return stand({ armR: 'up', armL: 'up', lean: -0.6, bob: -1, scared: true });
      return stand({ armR: 'fore', lean: 0.1 });
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
  /** Shoots a portal in front, steps in, pops out somewhere else — sometimes followed. */
  portalHop: {
    name: 'portalHop',
    dur: 4.6,
    speed: 0,
    pose: (t) => (t < 0.2 ? stand({ armR: 'fore', lean: 0.2 }) : t < 0.32 ? stand({ step: 1, lean: 0.4 }) : stand({ armR: 'up', smile: true })),
    alpha: (t) => (t < 0.2 ? 1 : t < 0.32 ? 1 - ramp(t, 0.2, 0.32) : t < 0.55 ? 0 : ramp(t, 0.55, 0.66)),
    fx: (ctx, x, gy, S, f, t) => {
      if (t < 0.4) {
        const open = Math.min(ramp(t, 0.05, 0.18), 1 - ramp(t, 0.32, 0.4));
        drawPortal(ctx, x + f * 4 * S, gy - 7 * S, 3.2 * S * open, t);
        if (t < 0.2) drawPortalGun(ctx, x + f * 3.6 * S, gy - 9 * S, S, f);
      } else if (t > 0.48 && t < 0.8) {
        const open = Math.min(ramp(t, 0.48, 0.56), 1 - ramp(t, 0.7, 0.8));
        drawPortal(ctx, x, gy - 7 * S, 3.2 * S * open, t);
      }
    },
    events: [
      { at: 0.45, run: (a, w) => (a.x = w.randomX(a.x)) },
      {
        at: 0.6,
        run: (a, w) => {
          if (Math.random() < 0.45) w.spawn(Math.random() < 0.6 ? 'blob' : 'saucer', a.x, a.facing, { follow: a, life: 6 });
        },
      },
    ],
  },
  jetpack: {
    name: 'jetpack',
    dur: 2.8,
    speed: 18,
    pose: (t) => stand({ bob: -Math.sin(t * Math.PI) * 16, armL: 'out', armR: 'out', smile: true }),
    fx: (ctx, x, gy, S, _f, t) => drawJetFlame(ctx, x, gy - Math.sin(t * Math.PI) * 16, S, t),
  },
  experiment: {
    name: 'experiment',
    dur: 2.6,
    speed: 0,
    pose: (t) => (t < 0.62 ? stand({ armR: 'fore', lean: 0.1 }) : stand({ armL: 'up', armR: 'up', scared: true, lean: -0.4 })),
    fx: (ctx, x, gy, S, f, t) => {
      if (t < 0.62) drawFlask(ctx, x + f * 4 * S, gy - 9 * S, S, t);
      else drawSmoke(ctx, x + f * 4 * S, gy - 10 * S, S, ramp(t, 0.62, 1));
    },
    events: [{ at: 0.64, run: (a, w) => w.say(a, pick(['…oops.', 'Science!', 'Note to self: less boom.']), 1.6) }],
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

  // ── THE TRAVELLER specials ──
  wandScan: {
    name: 'wandScan',
    dur: 2.2,
    speed: 0,
    pose: (t) => stand({ armR: 'up', bob: Math.sin(t * TAU) * 0.3, lean: Math.sin(t * Math.PI * 4) * 0.12 }),
    fx: (ctx, x, gy, S, f, t, def) => drawWand(ctx, x + f * 3.2 * S, gy - 10 * S, S, f, t, def?.wandGlow),
  },
  /** Summons the pod, steps in, vanishes; something wanders by; reappears elsewhere —
   *  sometimes in a NEW form. */
  podTrip: {
    name: 'podTrip',
    dur: 8.0,
    speed: 0,
    pose: (t) => (t < 0.18 ? stand({ armR: 'up' }) : stand({ step: t < 0.26 ? 1 : 0, lean: t < 0.26 ? 0.3 : 0, smile: t > 0.85 })),
    alpha: (t) => (t < 0.18 ? 1 : t < 0.26 ? 1 - ramp(t, 0.18, 0.26) : t < 0.84 ? 0 : ramp(t, 0.84, 0.92)),
    fx: (ctx, x, gy, S, f, t, def) => {
      // departure: pod at the old spot; arrival: at the new spot (x jumps at 0.7)
      let op = 0;
      if (t < 0.4) op = Math.min(ramp(t, 0, 0.12), 1 - ramp(t, 0.28, 0.4));
      else if (t >= 0.7) op = Math.min(ramp(t, 0.7, 0.8), 1 - ramp(t, 0.92, 1));
      drawTimePod(ctx, x + (t < 0.4 ? f * 2 * S : 0), gy, S, op, t * 8);
      if (t < 0.18) drawWand(ctx, x + f * 3.2 * S, gy - 10 * S, S, f, t * 8, def?.wandGlow);
    },
    events: [
      {
        at: 0.42,
        run: (a, w) => {
          // something slips out of the time wake: scary ones go after whoever is around,
          // friendly ones wait for the Traveller and tag along once he is back
          const k = pick(VISITORS_AFTER_POD);
          const friendly = k === 'duck' || k === 'saucer';
          w.spawn(k, a.x, Math.random() < 0.5 ? 1 : -1, friendly ? { life: 8, follow: a } : { life: 5.5 });
        },
      },
      {
        at: 0.7,
        run: (a, w) => {
          a.x = w.randomX(a.x);
          if (Math.random() < 0.4) nextForm(a); // the trip sometimes changes him
        },
      },
      { at: 0.9, run: (a, w) => w.say(a, pick(['Right on time.', 'Mind the paradox!', 'Wrong Tuesday. Again.', 'Back already!']), 1.8) },
    ],
  },
  /** Reform: a burst of sparkles and the Traveller has a new (original) look. */
  reform: {
    name: 'reform',
    dur: 2.4,
    speed: 0,
    pose: (t) => stand({ armL: 'out', armR: 'out', bob: -Math.sin(t * Math.PI) * 2, lean: Math.sin(t * Math.PI * 9) * 0.25, blink: t > 0.45 && t < 0.6 }),
    fx: (ctx, x, gy, S, _f, t) => drawReform(ctx, x, gy, S, t),
    events: [
      { at: 0.5, run: (a) => nextForm(a) },
      { at: 0.8, run: (a, w) => w.say(a, pick(['New face, same brain.', 'Hm. The ears are new.', 'Do I look taller?']), 1.8) },
    ],
  },
  tipHat: {
    name: 'tipHat',
    dur: 1.4,
    speed: 0,
    pose: (t) => stand({ lean: Math.sin(t * Math.PI) * 0.5, armR: t < 0.5 ? 'head' : 'down', bob: Math.sin(t * Math.PI) * 1, smile: true }),
  },
};

// Per-character action weights (DOC-R goofier; THE TRAVELLER calmer). Each only gets
// its own gadgets — DOC-R never summons the pod, the Traveller opens no portals.
export const WEIGHTS_DOCR: Record<string, number> = {
  idle: 4, walk: 5, wave: 2, jump: 3, think: 1, laugh: 3, trip: 2, point: 2, gadget: 1, sit: 1, dance: 2, glitch: 1,
  cheer: 2, shrug: 1, stretch: 1, lookAround: 2, facepalm: 1, run: 2,
  portalGun: 2, portalChaos: 2, portalHop: 3, jetpack: 2, experiment: 2, drink: 2, burp: 2,
};
export const WEIGHTS_TRAVELLER: Record<string, number> = {
  idle: 5, walk: 5, wave: 2, jump: 1, think: 4, laugh: 1, trip: 1, point: 3, gadget: 1, sit: 2, dance: 1, glitch: 1,
  cheer: 1, shrug: 2, stretch: 1, lookAround: 3, facepalm: 1, run: 1,
  wandScan: 3, podTrip: 3, reform: 2, tipHat: 2,
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

// Original quips, in the spirit of each archetype (no show catchphrases).
export const LINES_DOCR = [
  'Physics is more of a suggestion.',
  'Hold my flask.',
  "Don't lick the portal.",
  'That dimension owes me money.',
  'Who ordered tentacles?',
  'Trust me, I’m mostly a genius.',
  'Eh. Close enough.',
  'I invented that. Twice.',
];
export const LINES_TRAVELLER = [
  'Time waits for no one. Except me.',
  'I’ve seen this Tuesday before.',
  'Never trust a quiet century.',
  'Onwards!',
  'Brilliant. Absolutely brilliant.',
  'Have you tried turning time off and on?',
  'Quick, before yesterday ends!',
  'Mind the paradox.',
];
/** Joint-scene banter (index 0 = DOC-R, 1 = Traveller). */
export const ARGUE_LINES: [string, string][] = [
  ["That's not how SCIENCE works!", "That's not how TIME works!"],
  ['My gadget is bigger.', 'Mine folds into a teaspoon.'],
  ['You were late.', 'I was EARLY. Next week.'],
  ['Portals are faster.', 'Capsules are classier.'],
];

export { GW, GH };
