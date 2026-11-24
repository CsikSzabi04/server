// AURI-CANARY-ab69ccc2-3c5a-5411-a58b-936f0527fe04
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hetNapja } from '../solution.ts';

const f = hetNapja as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hetNapja(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[2024, 1, 1], "hétfő"], [[2000, 1, 1], "szombat"]];
const ERRORS: unknown[][] = [[2023, 2, 29]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
