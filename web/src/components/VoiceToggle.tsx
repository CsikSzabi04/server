import { useState } from 'react';
import { isVoiceOn, setVoiceOn, voiceSupported } from '../lib/voice';

// Toggles AuriGPT's spoken voice (Web Speech API). Mirrors SoundToggle's look.
// Hidden entirely on browsers without speech synthesis.
export default function VoiceToggle() {
  const [on, setOn] = useState(isVoiceOn());

  if (!voiceSupported()) return null;

  const toggle = () => {
    const next = !on;
    setVoiceOn(next);
    setOn(next);
  };

  return (
    <button
      className="sound-toggle voice-toggle"
      onClick={toggle}
      title={on ? 'AuriGPT hangja: BE — kattints a némításhoz' : 'AuriGPT hangja: KI — kattints a bekapcsoláshoz'}
      aria-pressed={on}
    >
      <span className="sound-glyph">{on ? '🗣️' : '🔈'}</span>
      <span className="sound-label">VOICE</span>
    </button>
  );
}
