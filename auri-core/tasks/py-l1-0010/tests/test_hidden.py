# AURI-CANARY-319adfe0-2fec-5687-b7fa-4ba86e12eb92
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import rle_dekodol

CASES = [(('',), ''), (('12a',), 'aaaaaaaaaaaa'), (('2ő1 ',), 'őő '), (('1a1b1a',), 'aba')]
ERRORS = [(('a',), 'ValueError'), (('3',), 'ValueError'), (('0a',), 'ValueError'), (('2a3',), 'ValueError')]


def _call(args: tuple) -> str:
    return "rle_dekodol(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(rle_dekodol(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                rle_dekodol(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
