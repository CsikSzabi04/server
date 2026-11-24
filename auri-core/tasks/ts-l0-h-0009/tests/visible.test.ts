// AURI-CANARY-21b52a1b-f037-5467-b5ef-fbbe23654e72
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ismetel } from '../solution.ts';

const f = ismetel as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `ismetel(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["ab", 3, "-"], "ab-ab-ab"], [["x", 0, ","], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
