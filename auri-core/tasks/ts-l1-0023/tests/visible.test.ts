// AURI-CANARY-a0ca6f67-e0c7-5d8e-afc8-098b04e814d9
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { masodikLegnagyobb } from '../solution.ts';

const f = masodikLegnagyobb as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `masodikLegnagyobb(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[3, 1, 4, 4]], 3], [[[5, 5]], null]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
