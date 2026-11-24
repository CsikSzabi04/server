// AURI-CANARY-ff0c7573-44a3-5046-9b76-a73a7e0e8c7f
// Reference solution: only for validating the task.
export function osszefesul(a: number[], b: number[]): number[] {
  const out: number[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) out.push(a[i] <= b[j] ? a[i++] : b[j++]);
  return [...out, ...a.slice(i), ...b.slice(j)];
}
