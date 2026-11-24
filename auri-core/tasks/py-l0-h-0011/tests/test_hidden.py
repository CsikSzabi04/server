# AURI-CANARY-ddf00700-7603-562a-ad9b-de29ca69f058
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import kumulalt

CASES = [(([5],), [5]), (([-1, 1, -1],), [-1, 0, -1]), (([0, 0],), [0, 0])]


def _call(args: tuple) -> str:
    return "kumulalt(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kumulalt(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
