# AURI-CANARY-766afb16-1347-57a4-b8ef-9024be4f3a20
import builtins
import copy
import unittest

from solution import mozgo_atlag

CASES = [(([1, 2, 3, 4], 2), [1.5, 2.5, 3.5]), (([1, 2], 3), [])]
ERRORS = [(([1], 0), 'ValueError')]


def _call(args: tuple) -> str:
    return "mozgo_atlag(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(mozgo_atlag(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                mozgo_atlag(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
