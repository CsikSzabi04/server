// AURI-CANARY-ed166b2d-0914-57e4-8ed9-27ee7aa313c4
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { atlagonFeluli } from '../solution.ts';

const f = atlagonFeluli as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `atlagonFeluli(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4]], [3, 4]], [[[]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
