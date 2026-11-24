// AURI-CANARY-9a5bb87e-fcb4-547e-b1ef-c630df26e604
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { snakeCamel } from '../solution.ts';

const f = snakeCamel as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `snakeCamel(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["parse_forint_value"], "parseForintValue"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
