# AURI-CANARY-406989fe-c7d3-5cd8-9b79-097f9d89619c
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import matrix_szorzas

CASES = [(([[1, 2, 3]], [[1], [2], [3]]), [[14]]),
 (([[2]], [[3]]), [[6]]),
 (([[1], [2]], [[3, 4]]), [[3, 4], [6, 8]]),
 (([[1, 0], [0, 1]], [[5, -1], [2, 7]]), [[5, -1], [2, 7]])]
ERRORS = [(([[1, 2]], [[1, 2]]), 'ValueError'), (([], [[1]]), 'ValueError'), (([[1]], []), 'ValueError')]


def _call(args: tuple) -> str:
    return "matrix_szorzas(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
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
