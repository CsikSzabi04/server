# AURI-CANARY-8a54431f-3a1b-5c4f-a310-b56feb209d18
import copy
import unittest

from solution import taj_ervenyes

CASES = [(('123456788',), True), (('123456789',), False)]


def _call(args: tuple) -> str:
    return "taj_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(taj_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
