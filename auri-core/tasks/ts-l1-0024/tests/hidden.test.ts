// AURI-CANARY-fd70fa72-93ae-5573-92d2-7a9f66cdea22
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sortores } from '../solution.ts';

const f = sortores as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `sortores(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["", 5], []], [["a b c", 1], ["a", "b", "c"]], [["a b c", 3], ["a b", "c"]], [["hosszúszó x", 4], ["hosszúszó", "x"]], [["  több   szóköz  ", 20], ["több szóköz"]], [["ab cd", 5], ["ab cd"]]];
const ERRORS: unknown[][] = [["x", 0]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
