// AURI-CANARY-f702c693-55a9-53bd-95ac-5440e3a3579e
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lepcso } from '../solution.ts';

const f = lepcso as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `lepcso(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[3], 3], [[0], 1]];
const ERRORS: unknown[][] = [[-1]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
