// AURI-CANARY-0ec46c2b-8d70-5397-a506-bd218f60e6d6
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamrendszer } from '../solution.ts';

const f = szamrendszer as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamrendszer(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[10, 2], "1010"], [[35, 36], "z"], [[36, 36], "10"], [[123456, 8], "361100"], [[7, 7], "10"]];
const ERRORS: unknown[][] = [[-1, 10], [5, 1], [5, 37]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
