// AURI-CANARY-f077ffbc-0ac3-5102-9aef-2a5b4adefa5b
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { maganhangzok } from '../solution.ts';

const f = maganhangzok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `maganhangzok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["Teszt Elek"], 3], [[""], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
