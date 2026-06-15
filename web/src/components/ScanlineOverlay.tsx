// Full-screen, non-interactive overlay: drifting scan bar + faint CRT grain.
export default function ScanlineOverlay() {
  return (
    <div className="scanline-overlay" aria-hidden="true">
      <div className="scan-bar" />
      <div className="scan-grain" />
    </div>
  );
}
