# AURI-CANARY-6ce2a96c-718b-52ed-9383-7b71dc575559
import builtins
import copy
import unittest

from solution import min_ermek

CASES = [((11, [1, 2, 5]), 3), ((3, [2]), -1)]
ERRORS = [((-1, [1]), 'ValueError')]


def _call(args: tuple) -> str:
    return "min_ermek(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(min_ermek(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                min_ermek(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
