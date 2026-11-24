// AURI-CANARY-955bf4bc-a70e-5dc6-9a8e-d76ca5049f58
// Reference solution: only for validating the task.
export function isbn10Ervenyes(s: string): boolean {
  const t = s.replace(/-/g, '');
  if (!/^[0-9]{9}[0-9X]$/.test(t)) return false;
  const d = [...t].map((c) => (c === 'X' ? 10 : Number(c)));
  return d.reduce((a, x, i) => a + (10 - i) * x, 0) % 11 === 0;
}
