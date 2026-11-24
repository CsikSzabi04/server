// AURI-CANARY-770b51a3-b3a1-5270-bd9f-4dbc204c81fb
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ezresTagolas } from '../solution.ts';

const f = ezresTagolas as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `ezresTagolas(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[1234567], "1 234 567"], [[0], "0"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
