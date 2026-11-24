// AURI-CANARY-387d39c3-fa79-516a-b1f6-25ee09f49adc
// Reference solution: only for validating the task.
export function binarisKereses(xs: number[], x: number): number {
  let lo = 0;
  let hi = xs.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (xs[mid] < x) lo = mid + 1;
    else hi = mid;
  }
  return lo < xs.length && xs[lo] === x ? lo : -1;
}
