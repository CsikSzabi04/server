# AURI-CANARY-de864572-4bf2-5dec-b9d2-9456db8b961e
import builtins
import copy
import unittest

from solution import median

CASES = [(([3, 1, 2],), 2), (([4, 1, 3, 2],), 2.5)]
ERRORS = [(([],), 'ValueError')]


def _call(args: tuple) -> str:
    return "median(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(median(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                median(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
