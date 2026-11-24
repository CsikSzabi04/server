# AURI-CANARY-f0bd89d7-2749-5f0c-adad-a07a7ea32ff4
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import forgat

CASES = [(([], 3), []),
 (([1, 2, 3], 0), [1, 2, 3]),
 (([1, 2, 3], 4), [3, 1, 2]),
 (([1, 2, 3], -1), [2, 3, 1]),
 (([1], 100), [1])]


def _call(args: tuple) -> str:
    return "forgat(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(forgat(*copy.deepcopy(args)), want, msg=_call(args))

    def test_nem_modosit(self) -> None:
        xs = [1, 2, 3]
        forgat(xs, 1)
        self.assertEqual(xs, [1, 2, 3], msg='forgat(xs, 1) után az xs változatlan')


if __name__ == "__main__":
    unittest.main()
