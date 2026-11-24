// AURI-CANARY-f5cb77f5-b3c3-567f-a871-56ebf8e35f08
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { darabol } from '../solution.ts';

const f = darabol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `darabol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[], 3], []], [[[1, 2], 5], [[1, 2]]], [[[1, 2, 3], 1], [[1], [2], [3]]], [[[1, 2, 3, 4], 2], [[1, 2], [3, 4]]]];
const ERRORS: unknown[][] = [[[1], 0], [[1], -2]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
