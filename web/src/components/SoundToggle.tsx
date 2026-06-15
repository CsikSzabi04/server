import { useState } from 'react';
import { blip, isMuted, setMuted } from '../lib/sound';

export default function SoundToggle() {
  const [muted, setM] = useState(isMuted());

  const toggle = () => {
    const next = !muted;
    setMuted(next);
    setM(next);
    if (!next) blip('recv'); // confirmation chirp when enabling
  };

  return (
    <button
      className="sound-toggle"
      onClick={toggle}
      title={muted ? 'Hangeffektek bekapcsolása' : 'Hangeffektek némítása'}
      aria-pressed={!muted}
    >
      <span className="sound-glyph">{muted ? '🔇' : '🔊'}</span>
      <span className="sound-label">{muted ? 'MUTE' : 'SND'}</span>
    </button>
  );
}
