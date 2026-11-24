// images.ts — pasted / dropped images → compact data: URLs for vision models.
// Screenshots of code must stay legible, so the long side is kept up to 1600 px and only
// the quality / size steps down until the image fits the proxy's per-image cap.
// Browser-only (canvas). The format check (parseDataUrl) is shared with the providers.

export const MAX_IMAGES = 4; // per request (the proxy enforces the same limit)
const MAX_SIDE = 1600;
const MAX_CHARS = 1_400_000; // < the proxy's 1.5M-char per-image cap

const DATA_URL = /^data:(image\/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/]+=*)$/;

/** Split an image data: URL into its MIME type and base64 payload (null if not allowed). */
export function parseDataUrl(url: string): { mime: string; data: string } | null {
  const m = DATA_URL.exec(url);
  return m ? { mime: m[1], data: m[2] } : null;
}

/** Downscale + compress an image file to a WebP (or JPEG) data: URL. */
export async function imageToDataUrl(file: Blob): Promise<string> {
  if (!file.type.startsWith('image/')) throw new Error('Not an image');
  const bmp = await createImageBitmap(file);
  try {
    let scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    let quality = 0.86;
    for (let attempt = 0; attempt < 6; attempt++) {
      const w = Math.max(1, Math.round(bmp.width * scale));
      const h = Math.max(1, Math.round(bmp.height * scale));
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Canvas is not available');
      ctx.fillStyle = '#fff'; // transparent screenshots stay readable once flattened
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(bmp, 0, 0, w, h);
      let url = canvas.toDataURL('image/webp', quality);
      if (!url.startsWith('data:image/webp')) url = canvas.toDataURL('image/jpeg', quality); // Safari
      if (url.length <= MAX_CHARS) return url;
      quality = Math.max(0.5, quality - 0.12);
      scale *= 0.8;
    }
    throw new Error('Image is too large');
  } finally {
    bmp.close();
  }
}

/** Image files from a paste / drop event (clipboard items or dropped files). */
export function imageFiles(data: DataTransfer | null): File[] {
  if (!data) return [];
  const out: File[] = [];
  for (const item of Array.from(data.items ?? [])) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const f = item.getAsFile();
      if (f) out.push(f);
    }
  }
  if (!out.length) for (const f of Array.from(data.files ?? [])) if (f.type.startsWith('image/')) out.push(f);
  return out;
}
