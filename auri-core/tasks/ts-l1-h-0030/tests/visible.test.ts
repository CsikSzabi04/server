// AURI-CANARY-8bf4781b-4cba-5eb0-89db-ae3f6f6d5306
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rpn } from '../solution.ts';

const f = rpn as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `rpn(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["3 4 +"], 7], [["5 1 2 + 4 * + 3 -"], 14]];
const ERRORS: unknown[][] = [[""]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
