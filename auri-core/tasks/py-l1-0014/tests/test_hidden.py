# AURI-CANARY-660c5b1a-dd4a-566b-95b3-c9b03d6e281c
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import statisztika

CASES = [(('',), {'betu': 0, 'szamjegy': 0, 'szokoz': 0, 'egyeb': 0}),
 (('é\t\n',), {'betu': 1, 'szamjegy': 0, 'szokoz': 2, 'egyeb': 0}),
 (('...',), {'betu': 0, 'szamjegy': 0, 'szokoz': 0, 'egyeb': 3})]


def _call(args: tuple) -> str:
    return "statisztika(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(statisztika(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
