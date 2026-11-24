# AURI-CANARY-c4feb925-5efe-56c6-baa4-8ac041c4b89f
import copy
import unittest

from solution import egyedi

CASES = [(([3, 1, 3, 2, 1],), [3, 1, 2])]


def _call(args: tuple) -> str:
    return "egyedi(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(egyedi(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
