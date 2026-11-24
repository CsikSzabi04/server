// AURI-CANARY-db9d8604-4d0e-5c08-a232-71d5e00d9284
// Reference solution: only for validating the task.
export function median(xs: number[]): number {
  if (!xs.length) throw new RangeError('üres');
  const s = [...xs].sort((a, b) => a - b);
  const n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
}
