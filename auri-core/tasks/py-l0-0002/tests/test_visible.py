# AURI-CANARY-40f2902b-c93a-50d1-9284-084857ed6c7e
import copy
import unittest

from solution import negyzetosszeg

CASES = [((3,), 14), ((0,), 0)]


def _call(args: tuple) -> str:
    return "negyzetosszeg(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(negyzetosszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
