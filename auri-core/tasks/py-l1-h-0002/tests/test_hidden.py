# AURI-CANARY-ce7c4603-dbab-56cc-89af-1bb67f28acae
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import szamrendszer

CASES = [((10, 2), '1010'), ((35, 36), 'z'), ((36, 36), '10'), ((123456, 8), '361100'), ((7, 7), '10')]
ERRORS = [((-1, 10), 'ValueError'), ((5, 1), 'ValueError'), ((5, 37), 'ValueError')]


def _call(args: tuple) -> str:
    return "szamrendszer(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szamrendszer(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                szamrendszer(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
