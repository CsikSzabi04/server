# AURI-CANARY-cd4c9e7f-e4e0-5def-be83-9ce69f7d0623
import copy
import unittest

from solution import ezres_tagolas

CASES = [((1234567,), '1 234 567'), ((0,), '0')]


def _call(args: tuple) -> str:
    return "ezres_tagolas(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ezres_tagolas(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
