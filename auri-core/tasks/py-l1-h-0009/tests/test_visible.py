# AURI-CANARY-406989fe-c7d3-5cd8-9b79-097f9d89619c
import builtins
import copy
import unittest

from solution import matrix_szorzas

CASES = [(([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]])]
ERRORS = [(([[1, 2]], [[1, 2]]), 'ValueError')]


def _call(args: tuple) -> str:
    return "matrix_szorzas(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(matrix_szorzas(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                matrix_szorzas(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
