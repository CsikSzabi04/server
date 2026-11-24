// AURI-CANARY-dfee3b81-f60f-5bc7-9787-b895a9abddeb
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tajErvenyes } from '../solution.ts';

const f = tajErvenyes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `tajErvenyes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["123456788"], true], [["123456789"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
