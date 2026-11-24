// AURI-CANARY-cc49b68d-c4a9-5f28-b10b-f4447957bba2
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { csucsok } from '../solution.ts';

const f = csucsok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `csucsok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 3, 2]], [1]], [[[]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
