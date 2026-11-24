// AURI-CANARY-587ca5d0-0f80-5dcb-b34a-8f69da65c135
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hamming } from '../solution.ts';

const f = hamming as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hamming(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["abc", "abc"], 0], [["abc", "abd"], 1], [["ő", "o"], 1], [["Alma", "alma"], 1]];
const ERRORS: unknown[][] = [["a", ""], ["ab", "abc"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
