// AURI-CANARY-1db1e144-c9ee-5842-b589-c196ed42eb92
// Reference solution: only for validating the task.
export function camelSnake(s: string): string {
  return [...s].map((c, i) => (i === 0 ? c.toLowerCase() : c !== c.toLowerCase() ? `_${c.toLowerCase()}` : c)).join('');
}
