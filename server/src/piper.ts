// Local, free neural text-to-speech via the Piper binary (rhasspy/piper).
// Runs entirely offline on CPU; we spawn the binary per request, feed text on
// stdin, and read back a WAV file. The public API surface stays stable so the
// backend could later swap to another TTS engine.
import { spawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { existsSync } from 'node:fs';
import { readFile, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { randomBytes } from 'node:crypto';
import { config } from './config';

export class PiperError extends Error {
  status: number;
  constructor(message: string, status = 503) {
    super(message);
    this.name = 'PiperError';
    this.status = status;
  }
}

// Paths in config are resolved against the server's working directory.
const binPath = (): string => resolve(process.cwd(), config.piperBin);
const defaultVoicePath = (): string => resolve(process.cwd(), config.piperVoice);

/** True only if TTS is enabled AND the binary + default voice are present. */
export function piperAvailable(): boolean {
  return config.piperEnabled && existsSync(binPath()) && existsSync(defaultVoicePath());
}

export interface SynthParams {
  text: string;
  voice?: string; // optional absolute/relative path to a .onnx voice override
  signal?: AbortSignal;
}

/** Synthesize speech; resolves to a complete WAV buffer (audio/wav). */
export async function synthesize(p: SynthParams): Promise<Buffer> {
  if (!config.piperEnabled) throw new PiperError('TTS disabled', 503);
  const bin = binPath();
  if (!existsSync(bin)) throw new PiperError(`piper binary not found at ${bin}`, 503);
  const voice = p.voice ? resolve(process.cwd(), p.voice) : defaultVoicePath();
  if (!existsSync(voice)) throw new PiperError('voice model not found', 400);

  const outFile = resolve(tmpdir(), `auri-tts-${randomBytes(8).toString('hex')}.wav`);

  try {
    await new Promise<void>((resolvePromise, reject) => {
      // cwd = the binary's folder so piper locates its bundled espeak-ng-data.
      const child = spawn(bin, ['--model', voice, '--output_file', outFile], {
        cwd: dirname(bin),
        windowsHide: true,
      });

      const err: Buffer[] = [];
      let settled = false;
      const finish = (fn: () => void) => {
        if (settled) return;
        settled = true;
        fn();
      };

      const timer = setTimeout(
        () => finish(() => { child.kill(); reject(new PiperError('piper timeout', 504)); }),
        config.piperTimeoutMs,
      );
      const onAbort = () =>
        finish(() => { clearTimeout(timer); child.kill(); reject(new PiperError('aborted', 499)); });
      p.signal?.addEventListener('abort', onAbort, { once: true });

      child.stderr.on('data', (d) => err.push(d as Buffer));
      child.on('error', (e) =>
        finish(() => { clearTimeout(timer); reject(new PiperError(`cannot start piper: ${e.message}`, 503)); }),
      );
      child.on('close', (code) =>
        finish(() => {
          clearTimeout(timer);
          p.signal?.removeEventListener('abort', onAbort);
          if (code === 0) resolvePromise();
          else
            reject(
              new PiperError(`piper failed (code ${code}): ${Buffer.concat(err).toString().slice(0, 200)}`, 502),
            );
        }),
      );

      child.stdin.on('error', () => {/* ignore EPIPE if the process already exited */});
      child.stdin.write(p.text);
      child.stdin.end();
    });

    const wav = await readFile(outFile);
    if (!wav.length) throw new PiperError('piper produced empty audio', 502);
    return wav;
  } finally {
    void unlink(outFile).catch(() => {/* best-effort cleanup */});
  }
}
