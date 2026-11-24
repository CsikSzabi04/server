# AURI-CANARY-da3844a0-e5ff-5ad1-a8d9-221569c068c3
import builtins
import copy
import unittest

from solution import hamming

CASES = [(('GAGCCT', 'CATCGT'), 3), (('', ''), 0)]
ERRORS = [(('a', ''), 'ValueError')]


def _call(args: tuple) -> str:
    return "hamming(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(hamming(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                hamming(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
