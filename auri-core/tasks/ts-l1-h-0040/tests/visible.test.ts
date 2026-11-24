// AURI-CANARY-69ffcce6-acd4-5f9f-b5a4-da272b68372c
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hexSzin } from '../solution.ts';

const f = hexSzin as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hexSzin(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["#ff8800"], [255, 136, 0]], [["#f80"], [255, 136, 0]]];
const ERRORS: unknown[][] = [["ff8800"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
