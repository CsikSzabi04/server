// AURI-CANARY-8a1f55bf-b062-5097-8c2d-3ccfde5e65fc
// Reference solution: only for validating the task.
export function luhn(s: string): boolean {
  const t = s.replace(/ /g, '');
  if (!/^[0-9]{2,}$/.test(t)) return false;
  let total = 0;
  [...t].reverse().forEach((c, i) => {
    let d = Number(c);
    if (i % 2 === 1) d = d > 4 ? d * 2 - 9 : d * 2;
    total += d;
  });
  return total % 10 === 0;
}
