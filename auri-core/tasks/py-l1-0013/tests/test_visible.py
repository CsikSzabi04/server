# AURI-CANARY-484c85b0-ba99-5cf0-95b4-abbfde8b3f07
import copy
import unittest

from solution import anagramma

CASES = [(('Listen', 'Silent'), True), (('alma', 'körte'), False)]


def _call(args: tuple) -> str:
    return "anagramma(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(anagramma(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
