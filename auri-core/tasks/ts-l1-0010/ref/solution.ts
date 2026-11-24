// AURI-CANARY-1a2c84ca-7892-5d7f-9af4-15f71a6c8d6a
// Reference solution: only for validating the task.
export function anagramma(a: string, b: string): boolean {
  const k = (s: string) => [...s.toLowerCase()].filter((c) => !/\s/.test(c)).sort().join('');
  return k(a) === k(b);
}
