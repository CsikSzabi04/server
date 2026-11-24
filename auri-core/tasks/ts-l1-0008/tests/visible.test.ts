// AURI-CANARY-ff0c7573-44a3-5046-9b76-a73a7e0e8c7f
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { osszefesul } from '../solution.ts';

const f = osszefesul as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `osszefesul(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 3, 5], [2, 4]], [1, 2, 3, 4, 5]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
