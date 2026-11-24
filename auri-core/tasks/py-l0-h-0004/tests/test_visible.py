# AURI-CANARY-33127245-a122-5ea8-86bc-1da3ec7c079b
import copy
import unittest

from solution import kozepso

CASES = [(('alma',), 'lm'), (('kerék',), 'r')]


def _call(args: tuple) -> str:
    return "kozepso(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kozepso(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
