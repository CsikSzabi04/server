# AURI-CANARY-34985e85-6a82-5388-bbed-d878e314cedd
import copy
import unittest

from solution import luhn

CASES = [(('79927398713',), True), (('79927398710',), False)]


def _call(args: tuple) -> str:
    return "luhn(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(luhn(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
