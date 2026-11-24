// AURI-CANARY-344656a8-e848-5362-9093-dbe2051c20ed
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kozosElotag } from '../solution.ts';

const f = kozosElotag as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kozosElotag(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[["virág", "virágzik", "virgonc"]], "vir"], [[[]], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
