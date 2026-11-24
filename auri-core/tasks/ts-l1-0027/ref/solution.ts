// AURI-CANARY-551aab1b-b170-5717-a2f4-def022cfe5b8
// Reference solution: only for validating the task.
export function datum(s: string): [number, number, number] {
  const m = /^(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\.$/.exec(s);
  if (!m) throw new RangeError(s);
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (mo < 1 || mo > 12 || d < 1 || d > days[mo - 1]) throw new RangeError(s);
  return [y, mo, d];
}
