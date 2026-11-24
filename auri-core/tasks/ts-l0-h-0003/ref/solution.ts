// AURI-CANARY-9f644fa5-f819-5139-9baf-6abf092cd8af
// Reference solution: only for validating the task.
export function elofordulas(xs: number[], x: number): number {
  return xs.filter((y) => y === x).length;
}
