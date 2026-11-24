// AURI-CANARY-69ffcce6-acd4-5f9f-b5a4-da272b68372c
// Reference solution: only for validating the task.
export function hexSzin(s: string): number[] {
  if (!/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(s)) throw new RangeError(s);
  let h = s.slice(1);
  if (h.length === 3) h = [...h].map((c) => c + c).join('');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}
