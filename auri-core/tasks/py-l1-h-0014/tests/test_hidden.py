# AURI-CANARY-c8234c43-0796-5f72-b68d-b84c1a304632
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import lnko_lista

CASES = [(([0, 0],), 0), (([-4, 6],), 2), (([17, 34, 51],), 17), (([9, 28],), 1), (([0, 5],), 5), (([-5],), 5)]
ERRORS = [(([],), 'ValueError')]


def _call(args: tuple) -> str:
    return "lnko_lista(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(lnko_lista(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                lnko_lista(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
