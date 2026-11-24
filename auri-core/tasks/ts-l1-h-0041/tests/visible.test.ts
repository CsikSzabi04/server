// AURI-CANARY-db9d8604-4d0e-5c08-a232-71d5e00d9284
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { median } from '../solution.ts';

const f = median as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `median(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[3, 1, 2]], 2], [[[4, 1, 3, 2]], 2.5]];
const ERRORS: unknown[][] = [[[]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
