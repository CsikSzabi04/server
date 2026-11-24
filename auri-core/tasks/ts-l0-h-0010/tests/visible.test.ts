// AURI-CANARY-48579f0a-bc56-5c2a-9fc9-bb2b2f474776
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { leghosszabbSzo } from '../solution.ts';

const f = leghosszabbSzo as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `leghosszabbSzo(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["a kutya ugat"], "kutya"], [[""], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
