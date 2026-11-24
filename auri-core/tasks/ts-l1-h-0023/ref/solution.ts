// AURI-CANARY-6f0b890a-f2e2-5e55-a64c-be38e41a33d9
// Reference solution: only for validating the task.
export function szamBetuvel(n: number): string {
  if (!(n >= 0 && n <= 99)) throw new RangeError(String(n));
  if (n === 0) return 'nulla';
  const EGY = ['', 'egy', 'kettő', 'három', 'négy', 'öt', 'hat', 'hét', 'nyolc', 'kilenc'];
  const TIZ = ['', 'tíz', 'húsz', 'harminc', 'negyven', 'ötven', 'hatvan', 'hetven', 'nyolcvan', 'kilencven'];
  const KOT = ['', 'tizen', 'huszon', ...TIZ.slice(3)];
  const t = Math.floor(n / 10);
  const e = n % 10;
  return e === 0 ? TIZ[t] : KOT[t] + EGY[e];
}
