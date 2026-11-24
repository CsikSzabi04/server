// AURI-CANARY-14ed2bff-e72b-574a-8d7e-9d8637f40bde
// Reference solution: only for validating the task.
export function lnkoLista(xs: number[]): number {
  if (!xs.length) throw new RangeError('üres');
  const g = (a: number, b: number): number => (b === 0 ? a : g(b, a % b));
  return xs.reduce((a, x) => g(a, Math.abs(x)), 0);
}
