// AURI-CANARY-ab69ccc2-3c5a-5411-a58b-936f0527fe04
// Reference solution: only for validating the task.
export function hetNapja(ev: number, ho: number, nap: number): string {
  const d = new Date(0);
  d.setUTCFullYear(ev, ho - 1, nap);
  if (d.getUTCFullYear() !== ev || d.getUTCMonth() !== ho - 1 || d.getUTCDate() !== nap) throw new RangeError(`${ev}-${ho}-${nap}`);
  return ['vasárnap', 'hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat'][d.getUTCDay()];
}
