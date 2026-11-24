// AURI-CANARY-05fc9fbd-09e4-57e4-be0a-0afad7f4df7f
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szigetek } from '../solution.ts';

const f = szigetek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szigetek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[["#.#", ".#.", "#.#"]], 5], [[["###", "#.#", "###"]], 1], [[["...", "..."]], 0], [[["#"]], 1], [[["##..", "#..#", "..##", "#..."]], 3]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
