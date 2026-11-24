// AURI-CANARY-d592ed01-d36c-57d2-8913-36317cd95aff
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ketOsszeg } from '../solution.ts';

const f = ketOsszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `ketOsszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[2, 7, 11, 15], 9], [0, 1]], [[[1, 2], 10], null]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
