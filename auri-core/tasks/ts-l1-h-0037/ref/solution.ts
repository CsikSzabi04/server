// AURI-CANARY-5d51b69d-2bb5-531c-84f8-0c7c39349b19
// Reference solution: only for validating the task.
export function egyensulyIndex(xs: number[]): number {
  const ossz = xs.reduce((a, b) => a + b, 0);
  let bal = 0;
  for (let i = 0; i < xs.length; i++) {
    if (bal === ossz - bal - xs[i]) return i;
    bal += xs[i];
  }
  return -1;
}
