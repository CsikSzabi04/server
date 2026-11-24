// AURI-CANARY-551aab1b-b170-5717-a2f4-def022cfe5b8
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { datum } from '../solution.ts';

const f = datum as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `datum(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["2026.11.21."], [2026, 11, 21]], [["2026. 11. 21."], [2026, 11, 21]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
