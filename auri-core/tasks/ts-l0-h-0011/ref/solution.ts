// AURI-CANARY-51605ed3-9981-5b53-918d-a02167792d9c
// Reference solution: only for validating the task.
export function kumulalt(xs: number[]): number[] {
  let s = 0;
  return xs.map((x) => (s += x));
}
