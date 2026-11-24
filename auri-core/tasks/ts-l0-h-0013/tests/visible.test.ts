// AURI-CANARY-e53a5fdd-3917-5585-9789-5b62212fe849
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { binaris } from '../solution.ts';

const f = binaris as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `binaris(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[5], "101"], [[0], "0"]];
const ERRORS: unknown[][] = [[-1]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
