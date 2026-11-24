// AURI-CANARY-a605c37e-b060-5b86-9596-9ab6e7c933e8
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamjegyosszeg } from '../solution.ts';

const f = szamjegyosszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamjegyosszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[-456], 15], [[9999], 36], [[1000000000000], 1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
