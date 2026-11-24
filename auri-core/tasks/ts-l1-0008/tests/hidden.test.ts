// AURI-CANARY-ff0c7573-44a3-5046-9b76-a73a7e0e8c7f
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { osszefesul } from '../solution.ts';

const f = osszefesul as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `osszefesul(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[], []], []], [[[], [1]], [1]], [[[1, 1], [1]], [1, 1, 1]], [[[-5, 0], [-6, 10]], [-6, -5, 0, 10]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
