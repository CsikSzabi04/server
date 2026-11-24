# AURI-CANARY-3380e876-a0bb-5a01-b389-a47c7cc227bb
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import honap_napjai

CASES = [((2023, 2), 28),
 ((1900, 2), 28),
 ((2000, 2), 29),
 ((2023, 4), 30),
 ((2023, 12), 31),
 ((2023, 11), 30),
 ((2023, 7), 31)]
ERRORS = [((2023, 0), 'ValueError'), ((2023, 13), 'ValueError')]


def _call(args: tuple) -> str:
    return "honap_napjai(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(honap_napjai(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                honap_napjai(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
