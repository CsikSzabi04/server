// AURI-CANARY-80029ac3-0715-5ac6-b026-3320dd631be4
// Reference solution: only for validating the task.
export function szamrendszerbol(s: string, b: number): number {
  const DIG = '0123456789abcdefghijklmnopqrstuvwxyz';
  if (b < 2 || b > 36 || s === '') throw new RangeError(s);
  let n = 0;
  for (const c of s.toLowerCase()) {
    const d = DIG.indexOf(c);
    if (d < 0 || d >= b) throw new RangeError(s);
    n = n * b + d;
  }
  return n;
}
