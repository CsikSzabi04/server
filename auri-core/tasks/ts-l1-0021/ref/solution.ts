// AURI-CANARY-3aa28cf9-ccaf-508e-8f6c-f2ea327d412e
// Reference solution: only for validating the task.
export function primek(n: number): number[] {
  if (n < 2) return [];
  const s = new Array<boolean>(n + 1).fill(true);
  s[0] = s[1] = false;
  for (let i = 2; i * i <= n; i++) if (s[i]) for (let j = i * i; j <= n; j += i) s[j] = false;
  return s.flatMap((p, i) => (p ? [i] : []));
}
