# AURI-CANARY-6c60b367-61f8-57a7-a28d-4d0193edce34
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import romai_szam

CASES = [((1,), 'I'), ((4,), 'IV'), ((3999,), 'MMMCMXCIX'), ((444,), 'CDXLIV'), ((90,), 'XC')]
ERRORS = [((0,), 'ValueError'), ((4000,), 'ValueError'), ((-5,), 'ValueError')]


def _call(args: tuple) -> str:
    return "romai_szam(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(romai_szam(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                romai_szam(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
