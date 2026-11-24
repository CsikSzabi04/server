// AURI-CANARY-90e057c9-65a3-5662-a737-1ff2dd6af0c5
// Reference solution: only for validating the task.
export function romaiSzam(n: number): string {
  if (!(n >= 1 && n <= 3999)) throw new RangeError(String(n));
  const P: [number, string][] = [[1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'],
    [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']];
  let out = '';
  for (const [v, r] of P) while (n >= v) { out += r; n -= v; }
  return out;
}
