// AURI-CANARY-cd986c0a-d877-5dd0-88f5-117e7a1128b6
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rleDekodol } from '../solution.ts';

const f = rleDekodol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `rleDekodol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["3a1b2c"], "aaabcc"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
