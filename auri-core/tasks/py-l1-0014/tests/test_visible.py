# AURI-CANARY-660c5b1a-dd4a-566b-95b3-c9b03d6e281c
import copy
import unittest

from solution import statisztika

CASES = [(('Alma 12!',), {'betu': 4, 'szamjegy': 2, 'szokoz': 1, 'egyeb': 1})]


def _call(args: tuple) -> str:
    return "statisztika(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(statisztika(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
