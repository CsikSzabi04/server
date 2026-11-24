# AURI-CANARY-c871a4fc-9c6e-5127-ae3e-573045c61376
import builtins
import copy
import unittest

from solution import rpn

CASES = [(('3 4 +',), 7), (('5 1 2 + 4 * + 3 -',), 14)]
ERRORS = [(('',), 'ValueError')]


def _call(args: tuple) -> str:
    return "rpn(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(rpn(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                rpn(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
