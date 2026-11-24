# AURI-CANARY-d39871a9-abea-50ed-aa5e-c7cd2e5100fb
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import telefonszam

CASES = [(('+36301234567',), '+36301234567'),
 (('36-20-765-4321',), '+36207654321'),
 (('(06) 70/111-2222',), '+36701112222'),
 (('06301234567',), '+36301234567')]
ERRORS = [(('',), 'ValueError'),
 (('30 123 4567',), 'ValueError'),
 (('06 30 123 456',), 'ValueError'),
 (('+3630123456a',), 'ValueError'),
 (('+36 30 123 45678',), 'ValueError')]


def _call(args: tuple) -> str:
    return "telefonszam(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(telefonszam(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                telefonszam(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
