# AURI-CANARY-ed5e3313-4689-570f-98ed-f9fe79dfae67
import builtins
import copy
import unittest

from solution import binaris

CASES = [((5,), '101'), ((0,), '0')]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "binaris(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(binaris(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                binaris(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
