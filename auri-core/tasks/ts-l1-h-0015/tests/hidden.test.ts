// AURI-CANARY-a9d8fb02-1aa0-5a67-850a-ee58abdfad10
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tokeletes } from '../solution.ts';

const f = tokeletes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `tokeletes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[28], true], [[496], true], [[8128], true], [[1], false], [[0], false], [[-6], false], [[12], false], [[33550336], true]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
