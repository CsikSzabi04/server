# AURI-CANARY-b125952b-42a0-51a4-b185-0020b7c2b34e
import copy
import unittest

from solution import ket_osszeg

CASES = [(([2, 7, 11, 15], 9), [0, 1]), (([1, 2], 10), None)]


def _call(args: tuple) -> str:
    return "ket_osszeg(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ket_osszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
