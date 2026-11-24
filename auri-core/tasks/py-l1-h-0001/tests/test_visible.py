# AURI-CANARY-46234616-18ea-547a-9fca-3314136ba8cf
import copy
import unittest

from solution import caesar

CASES = [(('abc', 1), 'bcd'), (('Zebra', 2), 'Bgdtc')]


def _call(args: tuple) -> str:
    return "caesar(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(caesar(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
