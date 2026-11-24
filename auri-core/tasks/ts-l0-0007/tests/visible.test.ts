// AURI-CANARY-f82cb7bb-b396-5fab-a0e0-5bea17ce6b70
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { celsiusFahrenheit } from '../solution.ts';

const f = celsiusFahrenheit as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `celsiusFahrenheit(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0], 32.0], [[100], 212.0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
