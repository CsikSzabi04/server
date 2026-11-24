// AURI-CANARY-9e635f6e-3906-5e5b-8c23-1e2dd1147076
// Reference solution: only for validating the task.
export function prim(n: number): boolean {
  if (n < 2) return false;
  for (let i = 2; i * i <= n; i++) if (n % i === 0) return false;
  return true;
}
