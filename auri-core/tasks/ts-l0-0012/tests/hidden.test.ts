// AURI-CANARY-648fdb1c-3891-5992-8d84-0d5e54434b40
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szorzotabla } from '../solution.ts';

const f = szorzotabla as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szorzotabla(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0], []], [[1], [[1]]], [[3], [[1, 2, 3], [2, 4, 6], [3, 6, 9]]], [[-1], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
