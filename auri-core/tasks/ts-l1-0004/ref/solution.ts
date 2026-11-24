// AURI-CANARY-f5cb77f5-b3c3-567f-a871-56ebf8e35f08
// Reference solution: only for validating the task.
export function darabol<T>(xs: T[], size: number): T[][] {
  if (size < 1) throw new RangeError(String(size));
  const out: T[][] = [];
  for (let i = 0; i < xs.length; i += size) out.push(xs.slice(i, i + size));
  return out;
}
