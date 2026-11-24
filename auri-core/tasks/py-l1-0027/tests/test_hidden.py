# AURI-CANARY-8e6bc047-3624-5673-839e-79ec01a97caa
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import sortores

CASES = [(('', 5), []),
 (('a b c', 1), ['a', 'b', 'c']),
 (('a b c', 3), ['a b', 'c']),
 (('hosszúszó x', 4), ['hosszúszó', 'x']),
 (('  több   szóköz  ', 20), ['több szóköz']),
 (('ab cd', 5), ['ab cd'])]
ERRORS = [(('x', 0), 'ValueError')]


def _call(args: tuple) -> str:
    return "sortores(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(sortores(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                sortores(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
