// AURI-CANARY-c560baf0-0154-5cd6-91c7-441a723aa2fa
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { teljesNegyzet } from '../solution.ts';

const f = teljesNegyzet as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `teljesNegyzet(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[16], true], [[15], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
