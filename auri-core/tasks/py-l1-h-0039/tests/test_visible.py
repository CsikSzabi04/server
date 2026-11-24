# AURI-CANARY-4da61ba7-7b21-5bc1-bfa2-bbdd71499d40
import builtins
import copy
import unittest

from solution import huszar

CASES = [(('b1',), ['a3', 'c3', 'd2']), (('a1',), ['b3', 'c2'])]
ERRORS = [(('i1',), 'ValueError')]


def _call(args: tuple) -> str:
    return "huszar(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(huszar(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                huszar(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
