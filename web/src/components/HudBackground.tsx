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

// Canvas layer: floating dust particles. (The rotating radar sweep from the center was
// removed at the user's request, 2026-11-21.) The grid is drawn with CSS (cheaper).
// Respects prefers-reduced-motion.
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
