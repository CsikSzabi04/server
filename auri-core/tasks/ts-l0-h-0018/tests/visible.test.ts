// AURI-CANARY-67e8e2a7-1ee2-5727-90c1-7155075cc44b
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { idoFormatum } from '../solution.ts';

const f = idoFormatum as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `idoFormatum(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[3661], "01:01:01"], [[0], "00:00:00"]];
const ERRORS: unknown[][] = [[-1]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
