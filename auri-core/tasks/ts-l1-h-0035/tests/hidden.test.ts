// AURI-CANARY-0fa1a00e-0330-50a8-95c1-411e6fee986e
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { levenshtein } from '../solution.ts';

const f = levenshtein as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `levenshtein(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["", "abc"], 3], [["abc", ""], 3], [["alma", "alma"], 0], [["flaw", "lawn"], 2], [["ház", "háziasszony"], 8], [["körte", "körtefa"], 2]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
