# AURI-CANARY-42363330-0e69-5a2c-b1e3-b28b4bd3a537
import copy
import unittest

from solution import paros_szamok

CASES = [(([1, 2, 3, 4],), [2, 4]), (([],), [])]


def _call(args: tuple) -> str:
    return "paros_szamok(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(paros_szamok(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
