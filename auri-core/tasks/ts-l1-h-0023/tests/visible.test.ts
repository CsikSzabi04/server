// AURI-CANARY-6f0b890a-f2e2-5e55-a64c-be38e41a33d9
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamBetuvel } from '../solution.ts';

const f = szamBetuvel as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamBetuvel(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[7], "hét"], [[21], "huszonegy"]];
const ERRORS: unknown[][] = [[-1]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
