// AURI-CANARY-d592ed01-d36c-57d2-8913-36317cd95aff
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ketOsszeg } from '../solution.ts';

const f = ketOsszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `ketOsszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[3, 3], 6], [0, 1]], [[[1, 2, 3, 4], 7], [2, 3]], [[[], 0], null], [[[0, 4, 3, 0], 0], [0, 3]], [[[5, 1, 5], 10], [0, 2]], [[[-1, 3, 4], 2], [0, 1]], [[[1, 5, 2, 4], 6], [0, 1]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
