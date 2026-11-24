// AURI-CANARY-f99ed2b4-482e-59a4-bc21-2210393a8a4d
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kezdobetuk } from '../solution.ts';

const f = kezdobetuk as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kezdobetuk(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["magyar tudományos akadémia"], "MTA"], [[""], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
