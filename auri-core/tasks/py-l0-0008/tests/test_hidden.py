# AURI-CANARY-c4feb925-5efe-56c6-baa4-8ac041c4b89f
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import egyedi

CASES = [(([],), []), (([5, 5, 5],), [5]), (([1, 2, 3],), [1, 2, 3]), (([-1, 0, -1, 0],), [-1, 0])]


def _call(args: tuple) -> str:
    return "egyedi(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(egyedi(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
