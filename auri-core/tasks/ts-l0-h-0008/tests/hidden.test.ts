// AURI-CANARY-c560baf0-0154-5cd6-91c7-441a723aa2fa
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { teljesNegyzet } from '../solution.ts';

const f = teljesNegyzet as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `teljesNegyzet(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0], true], [[-4], false], [[1000000], true], [[999999], false], [[1000000000000], true], [[1000000000001], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
