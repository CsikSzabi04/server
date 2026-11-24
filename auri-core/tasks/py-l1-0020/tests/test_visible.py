# AURI-CANARY-ae90ae24-b59f-570b-8aa5-3a91f504578e
import copy
import unittest

from solution import hossz_szerint

CASES = [((['a', 'bb', 'c'],), {1: ['a', 'c'], 2: ['bb']})]


def _call(args: tuple) -> str:
    return "hossz_szerint(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(hossz_szerint(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
