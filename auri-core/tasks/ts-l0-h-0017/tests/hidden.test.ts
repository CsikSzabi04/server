// AURI-CANARY-2240b986-d569-5f06-afce-0a485e38bbb2
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { vanIsmetlodes } from '../solution.ts';

const f = vanIsmetlodes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `vanIsmetlodes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[]], false], [[[0, 0]], true], [[[-1, 1]], false], [[[5, 4, 3, 2, 1, 5]], true]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
