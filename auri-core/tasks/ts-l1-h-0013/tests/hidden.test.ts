// AURI-CANARY-e1784f6e-46ce-5d2c-ac79-fc860ad2ad48
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { intervallumok } from '../solution.ts';

const f = intervallumok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `intervallumok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[[1, 2], [2, 3]]], [[1, 3]]], [[[[5, 6], [1, 2]]], [[1, 2], [5, 6]]], [[[[1, 10], [2, 3], [4, 5]]], [[1, 10]]], [[[[3, 3]]], [[3, 3]]], [[[[-5, -1], [-2, 0], [1, 1]]], [[-5, 0], [1, 1]]]];
const ERRORS: unknown[][] = [[[[2, 1]]], [[[1, 2], [5, 4]]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
