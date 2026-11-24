// AURI-CANARY-c2eadb07-5090-5b09-86c6-22e21c9d6dc7
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fizzbuzz } from '../solution.ts';

const f = fizzbuzz as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `fizzbuzz(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[5], ["1", "2", "Fizz", "4", "Buzz"]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
