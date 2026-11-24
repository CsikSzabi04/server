// AI-3 (BODY) — "⬇ AURI" download button, bottom-right of the AuriGPT web app (public name:
// "Auri" — spec §8: the J.A.R.V.I.S. name stays private). It sits ABOVE the bottom-right corner
// telemetry (CornerHud `.corner.br`) instead of on top of it, re-measured on resize.
// Links to the Windows installer on the GitHub Release (`latest` → no web redeploy per release).
// Override with VITE_AURI_DOWNLOAD_URL. Hidden on phones / narrow screens and in the desktop app.
import { type CSSProperties, useEffect, useLayoutEffect, useRef, useState } from 'react';
import './download.css';

const REPO = 'https://github.com/CsikSzabi04/server';
const DEFAULT_URL = `${REPO}/releases/latest/download/AuriSetup.exe`;
const RELEASES = `${REPO}/releases/latest`;
const GAP = 10;

function cornerOffset(): number {
  const br = document.querySelector('.corner.br');
  if (!br) return 14;
  const r = br.getBoundingClientRect();
  if (r.height === 0) return 14;
  return Math.max(14, Math.round(window.innerHeight - r.top + GAP));
}

export default function DownloadJarvis() {
  const url = (import.meta.env?.VITE_AURI_DOWNLOAD_URL as string | undefined)?.trim() || DEFAULT_URL;
  const [open, setOpen] = useState(false);
  const [bottom, setBottom] = useState(14);
  const boxRef = useRef<HTMLDivElement>(null);

  // stay clear of the corner telemetry (it mounts with the App and can change with the viewport)
  useLayoutEffect(() => {
    const place = () => setBottom(cornerOffset());
    place();
    const t1 = window.setTimeout(place, 300);
    const t2 = window.setTimeout(place, 1500);
    window.addEventListener('resize', place);
    const br = document.querySelector('.corner.br');
    const ro = br && 'ResizeObserver' in window ? new ResizeObserver(place) : null;
    if (br && ro) ro.observe(br);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.removeEventListener('resize', place);
      ro?.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="jvdl" ref={boxRef} style={{ bottom } as CSSProperties}>
      {open && (
        <div className="jvdl-card" role="dialog" aria-label="Auri letöltése">
          <div className="jvdl-title">
            AURI <span>// asztali app</span>
          </div>
          <p>
            A saját gépeden futó hangasszisztens: „Hey Auri”, helyi agy (Ollama), az AuriGPT kinézete, ARCHIVE és BRAIN —
            ugyanazzal a fiókkal.
          </p>
          <ul>
            <li>Windows 10 / 11 · 64 bit · 16 GB RAM ajánlott</li>
            <li>A telepítő kicsi; a futtatókörnyezetet és a modelleket telepítéskor tölti le (~2–5 GB, az Ollamával együtt)</li>
            <li>Rendszergazdai jog nem kell · eltávolítható a Programok közül</li>
          </ul>
          <a className="jvdl-go" href={url} rel="noopener">
            ⬇ AuriSetup.exe letöltése
          </a>
          <a className="jvdl-notes" href={RELEASES} target="_blank" rel="noopener noreferrer">
            Kiadási megjegyzések ↗
          </a>
        </div>
      )}
      <button
        className={`jvdl-btn${open ? ' on' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title="Auri letöltése Windowsra"
      >
        <span aria-hidden="true">⬇</span>
        <span className="jvdl-label">AURI</span>
      </button>
    </div>
  );
}
