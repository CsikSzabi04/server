# AURI-CANARY-6fbf813d-34b7-51eb-8b67-0b4e98de2849
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import idotartam_szoveg

CASES = [((60,), '1 perc'),
 ((7200,), '2 óra'),
 ((59,), '59 másodperc'),
 ((90061,), '25 óra 1 perc 1 másodperc'),
 ((3601,), '1 óra 1 másodperc')]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "idotartam_szoveg(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(idotartam_szoveg(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                idotartam_szoveg(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
