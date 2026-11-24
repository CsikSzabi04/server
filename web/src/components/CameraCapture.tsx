import { useEffect, useRef, useState } from 'react';

interface Props {
  onCapture: (photo: Blob) => void;
  onClose: () => void;
  /** No camera / permission denied → let the caller fall back to a file picker. */
  onUnavailable: (reason: string) => void;
}

// 📷 Take a photo with the computer's (or tablet's) camera. The stream lives only while
// this dialog is open and the frame stays in memory — nothing is uploaded or saved here;
// the caller turns it into a chat image like a pasted screenshot.
export default function CameraCapture({ onCapture, onClose, onUnavailable }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [facing, setFacing] = useState<'environment' | 'user'>('environment');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    if (!navigator.mediaDevices?.getUserMedia) {
      onUnavailable('Ebben a böngészőben nincs kamera-hozzáférés.');
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: facing, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const v = videoRef.current;
        if (v) {
          v.srcObject = stream;
          void v.play().then(() => setReady(true), () => setReady(true));
        }
      })
      .catch((e: Error) => {
        if (cancelled) return;
        onUnavailable(e.name === 'NotAllowedError' ? 'A kamera használata nincs engedélyezve.' : 'Nem található kamera.');
      });
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [facing, onUnavailable]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const snap = () => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext('2d')?.drawImage(v, 0, 0);
    c.toBlob((b) => b && onCapture(b), 'image/jpeg', 0.92);
  };

  return (
    <div className="camera-modal" role="dialog" aria-modal="true" aria-label="Fénykép készítése" onClick={onClose}>
      <div className="camera-box" onClick={(e) => e.stopPropagation()}>
        <video ref={videoRef} playsInline muted className="camera-video" />
        {!ready && <p className="camera-wait">Kamera indul…</p>}
        <div className="camera-actions">
          <button className="camera-btn" onClick={() => setFacing((f) => (f === 'user' ? 'environment' : 'user'))} title="Kamera váltása">
            ⟲
          </button>
          <button className="camera-btn camera-shoot" onClick={snap} disabled={!ready}>
            📸 Fotó
          </button>
          <button className="camera-btn" onClick={onClose}>
            Mégse
          </button>
        </div>
      </div>
    </div>
  );
}
