// AURI-CANARY-1db1e144-c9ee-5842-b589-c196ed42eb92
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { camelSnake } from '../solution.ts';

const f = camelSnake as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `camelSnake(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["parseForintValue"], "parse_forint_value"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
