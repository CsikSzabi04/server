// AURI-CANARY-648fdb1c-3891-5992-8d84-0d5e54434b40
// Reference solution: only for validating the task.
export function szorzotabla(n: number): number[][] {
  const r = Array.from({ length: Math.max(0, n) }, (_, i) => i + 1);
  return r.map((i) => r.map((j) => i * j));
}
