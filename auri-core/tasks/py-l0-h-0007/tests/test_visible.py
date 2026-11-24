# AURI-CANARY-0e97ffe8-0973-5f10-a001-5832a1068249
import copy
import unittest

from solution import haromszog

CASES = [((3, 4, 5), True), ((1, 2, 3), False)]


def _call(args: tuple) -> str:
    return "haromszog(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(haromszog(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
