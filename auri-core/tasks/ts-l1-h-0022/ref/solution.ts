// AURI-CANARY-fabad109-3944-58ec-8b68-81fb01b9a32f
// Reference solution: only for validating the task.
export function kombinacio(n: number, k: number): number {
  if (n < 0) throw new RangeError(String(n));
  if (k < 0 || k > n) return 0;
  k = Math.min(k, n - k);
  let r = 1;
  for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
  return r;
}
