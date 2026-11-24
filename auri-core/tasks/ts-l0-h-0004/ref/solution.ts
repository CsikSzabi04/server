// AURI-CANARY-5c308039-d9ee-5143-b432-4cacd1a9cbe6
// Reference solution: only for validating the task.
export function kozepso(s: string): string {
  const n = s.length;
  return n === 0 ? '' : s.slice(Math.floor((n - 1) / 2), Math.floor(n / 2) + 1);
}
