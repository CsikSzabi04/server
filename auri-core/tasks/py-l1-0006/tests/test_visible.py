# AURI-CANARY-6c60b367-61f8-57a7-a28d-4d0193edce34
import copy
import unittest

from solution import romai_szam

CASES = [((14,), 'XIV'), ((1994,), 'MCMXCIV')]


def _call(args: tuple) -> str:
    return "romai_szam(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(romai_szam(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
