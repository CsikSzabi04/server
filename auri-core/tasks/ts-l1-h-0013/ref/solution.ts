// AURI-CANARY-e1784f6e-46ce-5d2c-ac79-fc860ad2ad48
// Reference solution: only for validating the task.
export function intervallumok(iv: number[][]): number[][] {
  const s = iv.map((p) => [...p]).sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  const out: number[][] = [];
  for (const [a, b] of s) {
    if (a > b) throw new RangeError(`${a} ${b}`);
    const last = out[out.length - 1];
    if (last && a <= last[1]) last[1] = Math.max(last[1], b);
    else out.push([a, b]);
  }
  return out;
}
