// AURI-CANARY-8134cc76-809e-5388-8b19-6fb88b51c580
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tobbiSzorzata } from '../solution.ts';

const f = tobbiSzorzata as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `tobbiSzorzata(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4]], [24, 12, 8, 6]], [[[]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
