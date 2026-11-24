// AURI-CANARY-51605ed3-9981-5b53-918d-a02167792d9c
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kumulalt } from '../solution.ts';

const f = kumulalt as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kumulalt(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3]], [1, 3, 6]], [[[]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
