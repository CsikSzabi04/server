// AURI-CANARY-2857cad5-f249-515f-a19d-0a228abb7a10
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elsoEgyedi } from '../solution.ts';

const f = elsoEgyedi as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `elsoEgyedi(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], null], [["x"], "x"], [["aA"], "a"], [["kakukk"], "a"], [["abcabcd"], "d"], [["őrölő"], "r"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
