// AURI-CANARY-3aa28cf9-ccaf-508e-8f6c-f2ea327d412e
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { primek } from '../solution.ts';

const f = primek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `primek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[10], [2, 3, 5, 7]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
