# AURI-CANARY-4031638c-818e-5560-bb7c-5b852e19d921
import builtins
import copy
import unittest

from solution import intervallumok

CASES = [(([[1, 3], [2, 6], [8, 10]],), [[1, 6], [8, 10]]), (([],), [])]
ERRORS = [(([[2, 1]],), 'ValueError')]


def _call(args: tuple) -> str:
    return "intervallumok(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(intervallumok(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                intervallumok(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
