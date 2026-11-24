# AURI-CANARY-71816b23-6823-5477-ab0d-756ff4319a4e
import copy
import unittest

from solution import terjedelem

CASES = [(([3, 9, 1],), 8), (([],), 0)]


def _call(args: tuple) -> str:
    return "terjedelem(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(terjedelem(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
