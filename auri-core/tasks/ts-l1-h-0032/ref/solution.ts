// AURI-CANARY-cc49b68d-c4a9-5f28-b10b-f4447957bba2
// Reference solution: only for validating the task.
export function csucsok(xs: number[]): number[] {
  return xs.flatMap((x, i) => ((i === 0 || x > xs[i - 1]) && (i === xs.length - 1 || x > xs[i + 1]) ? [i] : []));
}
