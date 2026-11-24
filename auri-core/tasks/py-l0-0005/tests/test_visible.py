# AURI-CANARY-80f401a2-d116-56f1-83e5-d80695bcc180
import copy
import unittest

from solution import szamjegyosszeg

CASES = [((123,), 6), ((0,), 0)]


def _call(args: tuple) -> str:
    return "szamjegyosszeg(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szamjegyosszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
