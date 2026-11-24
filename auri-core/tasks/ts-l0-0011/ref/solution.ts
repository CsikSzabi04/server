// AURI-CANARY-c2eadb07-5090-5b09-86c6-22e21c9d6dc7
// Reference solution: only for validating the task.
export function fizzbuzz(n: number): string[] {
  return Array.from({ length: Math.max(0, n) }, (_, k) => {
    const i = k + 1;
    return i % 15 === 0 ? 'FizzBuzz' : i % 3 === 0 ? 'Fizz' : i % 5 === 0 ? 'Buzz' : String(i);
  });
}
