# AURI-CANARY-06fa3143-1beb-5ab8-bea5-bd2f8a01e44b
import builtins
import copy
import unittest

from solution import csv_sor

CASES = [(('a,b,c',), ['a', 'b', 'c']), (('"x,y",z',), ['x,y', 'z'])]
ERRORS = [(('"abc',), 'ValueError')]


def _call(args: tuple) -> str:
    return "csv_sor(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(csv_sor(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                csv_sor(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
