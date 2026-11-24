// AURI-CANARY-d72664bf-568f-53b9-96d7-bb23a6ca7731
// Reference solution: only for validating the task.
export function leghosszabbNovekvo(xs: number[]): number {
  let best = 0;
  let cur = 0;
  xs.forEach((x, i) => {
    cur = i && x > xs[i - 1] ? cur + 1 : 1;
    best = Math.max(best, cur);
  });
  return best;
}
