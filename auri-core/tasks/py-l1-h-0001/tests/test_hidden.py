# AURI-CANARY-46234616-18ea-547a-9fca-3314136ba8cf
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import caesar

CASES = [(('xyz', 3), 'abc'),
 (('abc', -1), 'zab'),
 (('Hello, World!', 27), 'Ifmmp, Xpsme!'),
 (('árvíz', 1), 'áswía'),
 (('abc', 0), 'abc'),
 (('', 5), ''),
 (('ABC', -27), 'ZAB')]


def _call(args: tuple) -> str:
    return "caesar(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(caesar(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
