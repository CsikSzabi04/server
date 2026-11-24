// AURI-CANARY-8134cc76-809e-5388-8b19-6fb88b51c580
// Reference solution: only for validating the task.
export function tobbiSzorzata(xs: number[]): number[] {
  const out = xs.map(() => 1);
  let p = 1;
  for (let i = 0; i < xs.length; i++) {
    out[i] = p;
    p *= xs[i];
  }
  p = 1;
  for (let i = xs.length - 1; i >= 0; i--) {
    out[i] *= p;
    p *= xs[i];
  }
  return out;
}
