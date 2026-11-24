// AURI-CANARY-7d3a29c7-565b-547e-8165-a1a626e49ff7
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { minErmek } from '../solution.ts';

const f = minErmek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `minErmek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0, [1]], 0], [[6, [1, 3, 4]], 2], [[7, [2, 4]], -1], [[100, [1, 5, 10, 25, 50]], 2], [[63, [1, 5, 10, 21, 25]], 3], [[1, []], -1]];
const ERRORS: unknown[][] = [[-1, [1]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
