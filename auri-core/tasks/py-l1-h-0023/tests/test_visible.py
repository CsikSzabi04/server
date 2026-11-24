# AURI-CANARY-5615f8b7-6077-57be-9bc4-5d3c35bda032
import builtins
import copy
import unittest

from solution import szam_betuvel

CASES = [((7,), 'hét'), ((21,), 'huszonegy')]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "szam_betuvel(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szam_betuvel(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                szam_betuvel(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
