# AURI-CANARY-b2ae44a1-1b79-54d0-9c58-a30741c61832
import copy
import unittest

from solution import modusz

CASES = [(([1, 2, 2, 3],), 2), (([],), None)]


def _call(args: tuple) -> str:
    return "modusz(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(modusz(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
