# AURI-CANARY-73b5bca8-862b-59ef-bee9-ad7bd048a729
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import kilapit

CASES = [(([],), []),
 (([[[]]],), []),
 (([1, (2, 3), [4]],), [1, (2, 3), 4]),
 (([['a'], 'bc'],), ['a', 'bc']),
 (([[[[[1]]]]],), [1])]


def _call(args: tuple) -> str:
    return "kilapit(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kilapit(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
