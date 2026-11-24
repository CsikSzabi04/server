// AURI-CANARY-233404da-e1f6-5ce8-8e49-7d049a346141
// Reference solution: only for validating the task.
export function maxIndex(xs: number[]): number {
  return xs.length ? xs.indexOf(Math.max(...xs)) : -1;
}
