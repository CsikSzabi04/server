// AURI-CANARY-31b45d03-56a8-54c8-9abb-00474dd1c4d8
// Reference solution: only for validating the task.
export function idotartamSzoveg(mp: number): string {
  if (mp < 0) throw new RangeError(String(mp));
  if (mp === 0) return '0 másodperc';
  const parts: [number, string][] = [[Math.floor(mp / 3600), 'óra'], [Math.floor((mp % 3600) / 60), 'perc'], [mp % 60, 'másodperc']];
  return parts.filter(([v]) => v).map(([v, n]) => `${v} ${n}`).join(' ');
}
