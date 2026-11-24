# AURI-CANARY-87ec13c6-605e-5216-a596-0d7d683425d9
import copy
import unittest

from solution import maganhangzok

CASES = [(('Teszt Elek',), 3), (('',), 0)]


def _call(args: tuple) -> str:
    return "maganhangzok(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(maganhangzok(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
