// AURI-CANARY-e1784f6e-46ce-5d2c-ac79-fc860ad2ad48
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { intervallumok } from '../solution.ts';

const f = intervallumok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `intervallumok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[[1, 3], [2, 6], [8, 10]]], [[1, 6], [8, 10]]], [[[]], []]];
const ERRORS: unknown[][] = [[[[2, 1]]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
