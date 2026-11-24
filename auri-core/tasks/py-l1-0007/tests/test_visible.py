# AURI-CANARY-703a1a4f-276e-5814-8e39-ed114a5c29c3
import copy
import unittest

from solution import darabol

CASES = [(([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])]


def _call(args: tuple) -> str:
    return "darabol(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(darabol(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
