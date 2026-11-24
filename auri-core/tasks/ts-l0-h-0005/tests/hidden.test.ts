// AURI-CANARY-4eee5193-3586-585c-a7b8-4f796a05db35
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szokoev } from '../solution.ts';

const f = szokoev as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szokoev(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[1900], false], [[2000], true], [[2100], false], [[1996], true]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
