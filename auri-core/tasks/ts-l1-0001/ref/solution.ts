// AURI-CANARY-560f1de0-5f80-53de-8269-51bd1f0a47db
// Reference solution: only for validating the task.
export function palindrom(s: string): boolean {
  const t = [...s.toLowerCase()].filter((c) => /[\p{L}\p{N}]/u.test(c));
  return t.join('') === [...t].reverse().join('');
}
