// AURI-CANARY-8a1f55bf-b062-5097-8c2d-3ccfde5e65fc
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { luhn } from '../solution.ts';

const f = luhn as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `luhn(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["79927398713"], true], [["79927398710"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
