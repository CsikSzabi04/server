// AURI-CANARY-8bf4781b-4cba-5eb0-89db-ae3f6f6d5306
// Reference solution: only for validating the task.
export function rpn(kif: string): number {
  const st: number[] = [];
  for (const t of kif.split(' ').filter(Boolean)) {
    if (/^-?[0-9]+$/.test(t)) st.push(Number(t));
    else if (t === '+' || t === '-' || t === '*') {
      if (st.length < 2) throw new RangeError('kevés operandus');
      const b = st.pop()!;
      const a = st.pop()!;
      st.push(t === '+' ? a + b : t === '-' ? a - b : a * b);
    } else throw new RangeError(t);
  }
  if (st.length !== 1) throw new RangeError('nem egy érték maradt');
  return st[0];
}
