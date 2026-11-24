// Full-screen, non-interactive overlay: faint CRT grain.
// (The top-to-bottom moving light bar was removed at the user's request, 2026-11-21.)
export default function ScanlineOverlay() {
  return (
    <div className="scanline-overlay" aria-hidden="true">
      <div className="scan-grain" />
    </div>
  );
}
