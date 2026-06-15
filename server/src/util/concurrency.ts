// Bounded-concurrency gate for CPU-bound inference. A single small model on CPU
// is fastest when not thrashed by many parallel decodes, so we cap how many
// requests hit Ollama at once and bound the waiting queue — overload then fails
// fast (503 server_busy) instead of piling up into timeouts.
import { config } from '../config';

export class Semaphore {
  private active = 0;
  private readonly waiters: Array<() => void> = [];

  constructor(
    private readonly max: number,
    private readonly queueLimit: number,
  ) {}

  get inflight(): number {
    return this.active;
  }
  get queued(): number {
    return this.waiters.length;
  }

  /**
   * Acquire a slot. Returns a Promise resolving to a release() fn, or `null`
   * immediately if the queue is full. Rejects (AbortError) if `signal` aborts
   * while waiting in the queue.
   */
  acquire(signal?: AbortSignal): Promise<() => void> | null {
    if (this.max <= 0) return Promise.resolve(() => {}); // 0/neg = unlimited
    if (this.active < this.max) {
      this.active++;
      return Promise.resolve(this.makeRelease());
    }
    if (this.waiters.length >= this.queueLimit) return null; // full -> caller 503s

    return new Promise<() => void>((resolve, reject) => {
      if (signal?.aborted) {
        reject(new DOMException('aborted', 'AbortError'));
        return;
      }
      const grant = () => {
        cleanup();
        this.active++;
        resolve(this.makeRelease());
      };
      const onAbort = () => {
        const i = this.waiters.indexOf(grant);
        if (i >= 0) this.waiters.splice(i, 1);
        cleanup();
        reject(new DOMException('aborted', 'AbortError'));
      };
      const cleanup = () => signal?.removeEventListener('abort', onAbort);
      signal?.addEventListener('abort', onAbort, { once: true });
      this.waiters.push(grant);
    });
  }

  private makeRelease(): () => void {
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this.active--;
      const next = this.waiters.shift();
      if (next) next();
    };
  }
}

// Shared singleton used by the chat route.
export const inferenceLimiter = new Semaphore(config.maxConcurrency, config.queueLimit);
