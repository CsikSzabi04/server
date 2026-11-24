// AURI-CANARY-0ec46c2b-8d70-5397-a506-bd218f60e6d6
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamrendszer } from '../solution.ts';

const f = szamrendszer as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamrendszer(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[255, 16], "ff"], [[0, 2], "0"]];
const ERRORS: unknown[][] = [[-1, 10]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
