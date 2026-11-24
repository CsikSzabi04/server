// AURI-CANARY-551aab1b-b170-5717-a2f4-def022cfe5b8
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { datum } from '../solution.ts';

const f = datum as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `datum(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["2024.2.29."], [2024, 2, 29]], [["2000.02.29."], [2000, 2, 29]], [["1999.12.31."], [1999, 12, 31]]];
const ERRORS: unknown[][] = [["2023.02.29."], ["1900.02.29."], ["2026.13.01."], ["2026.11.31."], ["2026.11.21"], ["2026-11-21"], [""], ["2026.00.10."]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
