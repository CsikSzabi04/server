import { useEffect, useRef } from 'react';

interface Props {
  /** Animation energy: 1 = idle, higher when thinking/speaking. */
  intensity?: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  a: number;
}

// Canvas layer: floating dust particles + a slow rotating radar sweep.
// The grid is drawn with CSS (cheaper). Respects prefers-reduced-motion.
export default function HudBackground({ intensity = 1 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const intensityRef = useRef(intensity);
  intensityRef.current = intensity;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const COUNT = reduce ? 0 : 42;

    let w = 0;
    let h = 0;
    let parts: Particle[] = [];
    let radar = 0;
    let raf = 0;

    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const init = () => {
      parts = Array.from({ length: COUNT }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        r: Math.random() * 1.6 + 0.4,
        a: Math.random() * 0.45 + 0.18,
      }));
    };

    const frame = () => {
      const k = intensityRef.current;
      ctx.clearRect(0, 0, w, h);

      // radar sweep — a faint rotating wedge from the center
      const cx = w * 0.5;
      const cy = h * 0.42;
      const R = Math.hypot(w, h);
      radar += 0.0022 * k;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(radar * Math.PI * 2);
      const g = ctx.createLinearGradient(0, 0, R, 0);
      g.addColorStop(0, `rgba(31,229,255,${0.06 * Math.min(1.5, k)})`);
      g.addColorStop(1, 'rgba(31,229,255,0)');
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, R, -0.2, 0);
      ctx.closePath();
      ctx.fillStyle = g;
      ctx.fill();
      ctx.restore();

      // particles
      for (const p of parts) {
        p.x += p.vx * k;
        p.y += p.vy * k;
        if (p.x < 0) p.x += w;
        else if (p.x > w) p.x -= w;
        if (p.y < 0) p.y += h;
        else if (p.y > h) p.y -= h;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(120,220,255,${p.a * Math.min(1.4, k)})`;
        ctx.fill();
      }

      if (!reduce) raf = requestAnimationFrame(frame);
    };

    resize();
    init();
    frame(); // draws at least one static frame even with reduced motion

    const onResize = () => {
      resize();
      init();
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, []);

  return <canvas ref={ref} className="hud-bg-canvas" aria-hidden="true" />;
}
