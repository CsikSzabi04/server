# AURI-CANARY-109efaad-7a66-5032-841f-886c17f01c0d
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import het_napja

CASES = [((1970, 1, 1), 'csütörtök'),
 ((2024, 2, 29), 'csütörtök'),
 ((1848, 3, 15), 'szerda'),
 ((1, 1, 1), 'hétfő'),
 ((9999, 12, 31), 'péntek')]
ERRORS = [((2023, 2, 29), 'ValueError'),
 ((2024, 2, 30), 'ValueError'),
 ((2024, 13, 1), 'ValueError'),
 ((2024, 4, 31), 'ValueError'),
 ((2024, 1, 0), 'ValueError')]


def _call(args: tuple) -> str:
    return "het_napja(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(het_napja(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                het_napja(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
