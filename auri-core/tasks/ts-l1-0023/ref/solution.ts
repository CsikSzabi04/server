// AURI-CANARY-a0ca6f67-e0c7-5d8e-afc8-098b04e814d9
// Reference solution: only for validating the task.
export function masodikLegnagyobb(xs: number[]): number | null {
  const u = [...new Set(xs)].sort((a, b) => a - b);
  return u.length >= 2 ? u[u.length - 2] : null;
}
