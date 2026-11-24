# AURI-CANARY-629c0c9a-1b1c-5238-b07c-b21c22c89e5e
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import romai_ertek

CASES = [(('iii',), 3), (('MMMCMXCIX',), 3999), (('XL',), 40), (('CDXLIV',), 444), (('I',), 1)]
ERRORS = [(('',), 'ValueError'), (('XIIZ',), 'ValueError'), (('12',), 'ValueError')]


def _call(args: tuple) -> str:
    return "romai_ertek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(romai_ertek(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                romai_ertek(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
