// AURI-CANARY-ab69ccc2-3c5a-5411-a58b-936f0527fe04
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hetNapja } from '../solution.ts';

const f = hetNapja as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hetNapja(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[1970, 1, 1], "csütörtök"], [[2024, 2, 29], "csütörtök"], [[1848, 3, 15], "szerda"], [[1, 1, 1], "hétfő"], [[9999, 12, 31], "péntek"]];
const ERRORS: unknown[][] = [[2023, 2, 29], [2024, 2, 30], [2024, 13, 1], [2024, 4, 31], [2024, 1, 0]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
