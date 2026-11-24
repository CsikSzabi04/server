// AURI-CANARY-9f644fa5-f819-5139-9baf-6abf092cd8af
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elofordulas } from '../solution.ts';

const f = elofordulas as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `elofordulas(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[0, 0, 0], 0], 3], [[[1, 2, 3], 4], 0], [[[-1, 1, -1], -1], 2]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
