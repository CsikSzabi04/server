# AURI-CANARY-1719af0a-7bef-5571-944e-320d96f0ac30
import copy
import unittest

from solution import forditott

CASES = [(('alma',), 'amla'), (('',), '')]


def _call(args: tuple) -> str:
    return "forditott(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(forditott(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
