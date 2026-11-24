// AURI-CANARY-6cfa9ec7-ed9c-5fe2-b7ab-db57715f3e24
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spiral } from '../solution.ts';

const f = spiral as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `spiral(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], [1, 2, 3, 6, 9, 8, 7, 4, 5]], [[[[1, 2], [3, 4], [5, 6]]], [1, 2, 4, 6, 5, 3]], [[[[1], [2], [3]]], [1, 2, 3]], [[[[1, 2, 3]]], [1, 2, 3]], [[[[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]], [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
