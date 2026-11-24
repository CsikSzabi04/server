# AURI-CANARY-d9683aef-489e-5c68-98be-c0f3edbba9db
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import datum

CASES = [(('2024.2.29.',), (2024, 2, 29)), (('2000.02.29.',), (2000, 2, 29)), (('1999.12.31.',), (1999, 12, 31))]
ERRORS = [(('2023.02.29.',), 'ValueError'),
 (('1900.02.29.',), 'ValueError'),
 (('2026.13.01.',), 'ValueError'),
 (('2026.11.31.',), 'ValueError'),
 (('2026.11.21',), 'ValueError'),
 (('2026-11-21',), 'ValueError'),
 (('',), 'ValueError'),
 (('2026.00.10.',), 'ValueError')]


def _call(args: tuple) -> str:
    return "datum(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(datum(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                datum(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
