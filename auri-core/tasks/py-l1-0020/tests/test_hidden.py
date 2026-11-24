# AURI-CANARY-ae90ae24-b59f-570b-8aa5-3a91f504578e
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import hossz_szerint

CASES = [(([],), {}),
 ((['alma', 'alma'],), {4: ['alma', 'alma']}),
 ((['', ''],), {0: ['', '']}),
 ((['ő', 'ab', 'x'],), {1: ['ő', 'x'], 2: ['ab']})]


def _call(args: tuple) -> str:
    return "hossz_szerint(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(hossz_szerint(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
