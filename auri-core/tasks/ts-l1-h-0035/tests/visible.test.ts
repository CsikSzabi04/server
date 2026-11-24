// AURI-CANARY-0fa1a00e-0330-50a8-95c1-411e6fee986e
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { levenshtein } from '../solution.ts';

const f = levenshtein as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `levenshtein(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["kitten", "sitting"], 3], [["", ""], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
