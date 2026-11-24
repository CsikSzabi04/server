# AURI-CANARY-35343a44-f007-55ac-8547-2af677805881
import copy
import unittest

from solution import permutaciok

CASES = [(('ab',), ['ab', 'ba']), (('',), [''])]


def _call(args: tuple) -> str:
    return "permutaciok(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(permutaciok(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
