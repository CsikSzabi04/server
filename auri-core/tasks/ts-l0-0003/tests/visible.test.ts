// AURI-CANARY-15e087e4-595d-5c3d-a90e-ab5245501f76
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { forditott } from '../solution.ts';

const f = forditott as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `forditott(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["alma"], "amla"], [[""], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
