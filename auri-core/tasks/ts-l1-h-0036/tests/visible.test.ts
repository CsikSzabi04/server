// AURI-CANARY-1faa60ea-36b9-5973-b1a8-ccca50194756
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szoMinta } from '../solution.ts';

const f = szoMinta as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szoMinta(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["abba", "kutya macska macska kutya"], true], [["abba", "kutya macska macska hal"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
