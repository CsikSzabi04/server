# AURI-CANARY-c871a4fc-9c6e-5127-ae3e-573045c61376
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import rpn

CASES = [(('42',), 42), (('-3 2 *',), -6), (('2 3 -',), -1), (('  1   2 +  ',), 3), (('1 2 3 * +',), 7)]
ERRORS = [(('',), 'ValueError'),
 (('1 +',), 'ValueError'),
 (('1 2',), 'ValueError'),
 (('1 2 /',), 'ValueError'),
 (('a',), 'ValueError'),
 (('+',), 'ValueError')]


def _call(args: tuple) -> str:
    return "rpn(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
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
