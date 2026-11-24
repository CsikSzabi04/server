// AURI-CANARY-6cfa9ec7-ed9c-5fe2-b7ab-db57715f3e24
// Reference solution: only for validating the task.
export function spiral(m: number[][]): number[] {
  const out: number[] = [];
  let top = 0;
  let bot = m.length - 1;
  let left = 0;
  let right = (m[0]?.length ?? 0) - 1;
  while (top <= bot && left <= right) {
    for (let j = left; j <= right; j++) out.push(m[top][j]);
    top++;
    for (let i = top; i <= bot; i++) out.push(m[i][right]);
    right--;
    if (top <= bot) {
      for (let j = right; j >= left; j--) out.push(m[bot][j]);
      bot--;
    }
    if (left <= right) {
      for (let i = bot; i >= top; i--) out.push(m[i][left]);
      left++;
    }
  }
  return out;
}
