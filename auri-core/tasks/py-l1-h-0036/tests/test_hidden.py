# AURI-CANARY-3e2c44de-20ea-59f3-a3d9-5055539751a5
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szo_minta

CASES = [(('aaaa', 'kutya kutya kutya kutya'), True),
 (('abba', 'kutya kutya kutya kutya'), False),
 (('ab', 'kutya'), False),
 (('', ''), True),
 (('ab', 'x x'), False),
 (('ab', 'x y'), True),
 (('aab', 'x x y'), True)]


def _call(args: tuple) -> str:
    return "szo_minta(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szo_minta(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
