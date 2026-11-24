// AURI-CANARY-88f3633a-699d-5964-8183-cd0951d9f7ea
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { permutaciok } from '../solution.ts';

const f = permutaciok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `permutaciok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["aab"], ["aab", "aba", "baa"]], [["abc"], ["abc", "acb", "bac", "bca", "cab", "cba"]], [["x"], ["x"]], [["Ba"], ["Ba", "aB"]], [["aaa"], ["aaa"]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
