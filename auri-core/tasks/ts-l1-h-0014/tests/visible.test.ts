// AURI-CANARY-14ed2bff-e72b-574a-8d7e-9d8637f40bde
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lnkoLista } from '../solution.ts';

const f = lnkoLista as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `lnkoLista(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[12, 18]], 6], [[[7]], 7]];
const ERRORS: unknown[][] = [[[]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
