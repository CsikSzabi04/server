# AURI-CANARY-a8c3c770-f2df-5fe1-8ddc-6eac52f41405
import copy
import unittest

from solution import max_index

CASES = [(([1, 5, 3],), 1), (([],), -1)]


def _call(args: tuple) -> str:
    return "max_index(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(max_index(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
