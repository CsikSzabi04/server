# AURI-CANARY-5afdc06c-c900-5603-bcb2-5c528cf717b5
import builtins
import copy
import unittest

from solution import lepcso

CASES = [((3,), 3), ((0,), 1)]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "lepcso(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(lepcso(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                lepcso(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
