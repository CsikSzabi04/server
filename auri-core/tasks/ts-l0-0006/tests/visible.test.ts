// AURI-CANARY-abea2614-d391-500c-88f6-c7e6214cd603
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szavakSzama } from '../solution.ts';

const f = szavakSzama as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szavakSzama(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["alma körte"], 2], [[""], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
