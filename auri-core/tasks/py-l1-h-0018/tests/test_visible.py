# AURI-CANARY-7cbd345c-f908-554a-94ad-a8efe0595472
import copy
import unittest

from solution import pangramma

CASES = [(('The quick brown fox jumps over the lazy dog',), True), (('abc',), False)]


def _call(args: tuple) -> str:
    return "pangramma(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(pangramma(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
