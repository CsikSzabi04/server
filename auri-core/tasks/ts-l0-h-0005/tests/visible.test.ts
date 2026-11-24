// AURI-CANARY-4eee5193-3586-585c-a7b8-4f796a05db35
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szokoev } from '../solution.ts';

const f = szokoev as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szokoev(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[2024], true], [[2023], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
