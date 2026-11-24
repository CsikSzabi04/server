// AURI-CANARY-6c95c76a-3702-5ecb-8c1e-b8c7f53c286d
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rleKodol } from '../solution.ts';

const f = rleKodol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `rleKodol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], ""], [["a"], "1a"], [["aaaaaaaaaaaa"], "12a"], [["abab"], "1a1b1a1b"], [["őőű  "], "2ő1ű2 "]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
