// AURI-CANARY-387d39c3-fa79-516a-b1f6-25ee09f49adc
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { binarisKereses } from '../solution.ts';

const f = binarisKereses as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `binarisKereses(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[], 1], -1], [[[2, 2, 2], 2], 0], [[[1, 2, 2, 3], 2], 1], [[[1], 1], 0], [[[0, 2, 4, 6, 8, 10], 10], 5], [[[1, 3], 0], -1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
