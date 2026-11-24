// AURI-CANARY-181474df-baad-5055-a0e6-774e14139208
// Reference solution: only for validating the task.
export function csere(s: string): string {
  return [...s].map((c) => (c === c.toUpperCase() ? c.toLowerCase() : c.toUpperCase())).join('');
}
