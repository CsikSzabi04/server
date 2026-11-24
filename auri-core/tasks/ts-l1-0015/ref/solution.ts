// AURI-CANARY-7d8c4ff5-5e0e-58f0-8f6a-91ef8b761cac
// Reference solution: only for validating the task.
export function idotartamMp(s: string): number {
  const ORDER: Record<string, [number, number]> = { h: [0, 3600], m: [1, 60], s: [2, 1] };
  let total = 0;
  let last = -1;
  for (const part of s.split(' ')) {
    const m = /^(\d+)([hms])$/.exec(part);
    if (!m || ORDER[m[2]][0] <= last) throw new RangeError(s);
    last = ORDER[m[2]][0];
    total += Number(m[1]) * ORDER[m[2]][1];
  }
  return total;
}
