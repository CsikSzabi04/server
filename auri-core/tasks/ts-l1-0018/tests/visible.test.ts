// AURI-CANARY-9ced5d8f-9918-53d2-85ee-dfbe980180a2
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { forgat } from '../solution.ts';

const f = forgat as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `forgat(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4], 1], [4, 1, 2, 3]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
