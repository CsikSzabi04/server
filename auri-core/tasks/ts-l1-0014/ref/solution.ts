// AURI-CANARY-dfee3b81-f60f-5bc7-9787-b895a9abddeb
// Reference solution: only for validating the task.
export function tajErvenyes(s: string): boolean {
  if (!/^(\d{9}|\d{3} \d{3} \d{3})$/.test(s)) return false;
  const d = [...s.replaceAll(' ', '')].map(Number);
  return d.slice(0, 8).reduce((a, x, i) => a + x * (i % 2 === 0 ? 3 : 7), 0) % 10 === d[8];
}
