# AURI-CANARY-49536514-79da-5829-b792-d05fcb8358b8
import copy
import unittest

from solution import osszefesul

CASES = [(([1, 3, 5], [2, 4]), [1, 2, 3, 4, 5])]


def _call(args: tuple) -> str:
    return "osszefesul(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(osszefesul(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
