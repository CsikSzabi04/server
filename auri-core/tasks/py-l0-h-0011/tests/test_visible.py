# AURI-CANARY-ddf00700-7603-562a-ad9b-de29ca69f058
import copy
import unittest

from solution import kumulalt

CASES = [(([1, 2, 3],), [1, 3, 6]), (([],), [])]


def _call(args: tuple) -> str:
    return "kumulalt(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kumulalt(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
