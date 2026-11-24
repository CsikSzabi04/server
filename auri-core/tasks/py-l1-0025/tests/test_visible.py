# AURI-CANARY-24dc8a0e-5dc9-5b07-bcc5-3ca97f3ca1f0
import copy
import unittest

from solution import transzponal

CASES = [(([[1, 2, 3], [4, 5, 6]],), [[1, 4], [2, 5], [3, 6]])]


def _call(args: tuple) -> str:
    return "transzponal(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(transzponal(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
