// AURI-CANARY-9ced5d8f-9918-53d2-85ee-dfbe980180a2
// Reference solution: only for validating the task.
export function forgat<T>(xs: T[], k: number): T[] {
  const n = xs.length;
  if (!n) return [];
  const r = ((k % n) + n) % n;
  return r ? [...xs.slice(n - r), ...xs.slice(0, n - r)] : [...xs];
}
