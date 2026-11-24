// AURI-CANARY-7db0188c-9817-53d7-8939-433fb0f4838f
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { egyedi } from '../solution.ts';

const f = egyedi as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `egyedi(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[3, 1, 3, 2, 1]], [3, 1, 2]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
