// AURI-CANARY-85358d24-0e4a-5816-8d23-2cf60074854d
// Reference solution: only for validating the task.
export function zarojelek(s: string): boolean {
  const st: string[] = [];
  const pair: Record<string, string> = { ')': '(', ']': '[', '}': '{' };
  for (const c of s) {
    if ('([{'.includes(c)) st.push(c);
    else if (c in pair && st.pop() !== pair[c]) return false;
  }
  return st.length === 0;
}
