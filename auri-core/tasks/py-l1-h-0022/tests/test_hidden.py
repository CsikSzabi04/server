# AURI-CANARY-7c79804c-b658-54e3-b1ae-af97f1a54553
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import kombinacio

CASES = [((0, 0), 1), ((10, 0), 1), ((10, 10), 1), ((4, -1), 0), ((20, 10), 184756), ((50, 25), 126410606437752)]
ERRORS = [((-1, 0), 'ValueError')]


def _call(args: tuple) -> str:
    return "kombinacio(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kombinacio(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                kombinacio(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
