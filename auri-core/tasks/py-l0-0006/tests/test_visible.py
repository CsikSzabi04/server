# AURI-CANARY-fde339dd-9997-5ec9-85dd-c359fd6feead
import copy
import unittest

from solution import szavak_szama

CASES = [(('alma körte',), 2), (('',), 0)]


def _call(args: tuple) -> str:
    return "szavak_szama(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szavak_szama(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
